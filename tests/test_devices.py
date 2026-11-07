"""Simulated CUDA routing/failures; these tests do not claim GPU execution."""

import sys
from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from PIL import Image

from lumacaption.engine import MODEL_REVISION, CaptionEngine, CaptionOptions, ModelUnavailableError


@pytest.fixture
def runtime(monkeypatch):
    state = SimpleNamespace(
        available=True,
        probe_error=None,
        probes=0,
        moves=[],
        inputs=[],
        loads=[],
        fail_moves=set(),
        failures=[],
        generated=[],
        cpu_threads=[],
        transfers=[],
    )

    class OutOfMemoryError(RuntimeError):
        pass

    class Tensor:
        def __init__(self, dtype):
            self.dtype = dtype
            self.device = "cpu"

        def to(self, device):
            state.transfers.append((self.dtype, device))
            self.device = device
            return self

    class Processor:
        def __call__(self, *, images, return_tensors):
            assert return_tensors == "pt"
            state.inputs.append(images)
            return {
                "pixel_values": Tensor("float32"),
                "input_ids": Tensor("int64"),
                "attention_mask": Tensor("int64"),
            }

        def decode(self, tokens, *, skip_special_tokens):
            assert skip_special_tokens
            return "a test caption"

    class Model:
        device = "cpu"

        def to(self, device):
            state.moves.append(device)
            if device in state.fail_moves:
                raise RuntimeError("simulated placement failure")
            self.device = device
            return self

        def eval(self):
            return self

        def generate(self, **kwargs):
            assert all(
                kwargs[key].device == self.device
                for key in ("pixel_values", "input_ids", "attention_mask")
            )
            state.generated.append(self.device)
            assert kwargs["max_new_tokens"] == 35
            assert kwargs["num_beams"] == 3
            assert kwargs["do_sample"] is False and kwargs["no_repeat_ngram_size"] == 3
            if state.failures:
                error = state.failures.pop(0)
                if error:
                    raise error
            return [["tokens"]]

    def load(kind, obj, *args, **kwargs):
        state.loads.append((kind, kwargs))
        assert kwargs["local_files_only"] is True
        assert kwargs["revision"] == MODEL_REVISION
        assert kwargs["token"] is False
        if kind == "model":
            assert kwargs["weights_only"] is True and kwargs["use_safetensors"] is False
        return obj

    def available():
        state.probes += 1
        if state.probe_error:
            raise state.probe_error
        return state.available

    state.oom = OutOfMemoryError
    state.model = Model()
    processor = Processor()
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(
            cuda=SimpleNamespace(is_available=available, OutOfMemoryError=OutOfMemoryError),
            set_num_threads=state.cpu_threads.append,
            inference_mode=nullcontext,
        ),
    )
    monkeypatch.setitem(sys.modules, "truststore", SimpleNamespace(inject_into_ssl=lambda: None))
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            BlipProcessor=SimpleNamespace(
                from_pretrained=lambda *a, **kw: load("processor", processor, *a, **kw)
            ),
            BlipForConditionalGeneration=SimpleNamespace(
                from_pretrained=lambda *a, **kw: load("model", state.model, *a, **kw)
            ),
        ),
    )
    return state


def generate(engine):
    with Image.new("RGB", (8, 8)) as image:
        return engine.caption(image, CaptionOptions())


def test_default_cpu_never_probes_cuda_and_reuses_model(runtime):
    engine = CaptionEngine(offline=True)
    assert generate(engine) == "A test caption"
    assert generate(engine) == "A test caption"
    assert engine.device == "cpu" and not engine.fallback_reason
    assert runtime.probes == 0 and runtime.moves == ["cpu"]
    assert len(runtime.loads) == 2 and len(runtime.cpu_threads) == 1


def test_cuda_places_model_and_all_inputs_without_casting_integer_tokens(runtime):
    engine = CaptionEngine(offline=True, device="cuda")
    messages = []
    engine.prepare(messages.append)
    assert generate(engine) == "A test caption"
    assert engine.device == "cuda" and not engine.fallback_reason
    assert runtime.moves == ["cuda"]
    assert runtime.transfers == [("float32", "cuda"), ("int64", "cuda"), ("int64", "cuda")]
    assert "CUDA" in messages[-1]


@pytest.mark.parametrize("failure", ["unavailable", "probe", "placement"])
def test_cuda_setup_falls_back_once_and_reports_actual_device(runtime, failure):
    if failure == "unavailable":
        runtime.available = False
    elif failure == "probe":
        runtime.probe_error = RuntimeError("driver unavailable")
    else:
        runtime.fail_moves.add("cuda")
    engine = CaptionEngine(offline=True, device="cuda")
    messages = []
    engine.prepare(messages.append)
    assert generate(engine) == "A test caption"
    assert engine.requested_device == "cuda" and engine.device == "cpu"
    assert engine.fallback_reason and "CPU fallback" in messages[-1]
    other_messages = []
    engine.prepare(other_messages.append)
    assert "CPU fallback" in other_messages[-1]
    assert runtime.probes == 1 and len(runtime.loads) == 2


def test_cuda_oom_retries_current_image_once_then_keeps_cpu(runtime):
    runtime.failures = [runtime.oom("full"), None]
    engine = CaptionEngine(offline=True, device="cuda")
    messages = []
    engine.prepare(messages.append)
    assert generate(engine) == "A test caption"
    assert generate(engine) == "A test caption"
    assert runtime.generated == ["cuda", "cpu", "cpu"]
    assert runtime.moves == ["cuda", "cpu"]
    assert engine.device == "cpu" and "out of memory" in engine.fallback_reason
    assert "CPU fallback" in messages[-1]


def test_failed_cpu_retry_is_not_retried_again(runtime):
    runtime.failures = [runtime.oom("GPU full"), runtime.oom("CPU full")]
    engine = CaptionEngine(offline=True, device="cuda")
    with pytest.raises(runtime.oom, match="CPU full"):
        generate(engine)
    assert runtime.generated == ["cuda", "cpu"]


def test_cpu_oom_is_not_treated_as_cuda_fallback(runtime):
    runtime.failures = [runtime.oom("CPU full")]
    with pytest.raises(runtime.oom):
        generate(CaptionEngine(offline=True))
    assert runtime.generated == ["cpu"] and runtime.moves == ["cpu"]


def test_non_memory_generation_error_remains_an_error(runtime):
    runtime.failures = [RuntimeError("model error")]
    with pytest.raises(RuntimeError, match="model error"):
        generate(CaptionEngine(offline=True, device="cuda"))
    assert runtime.generated == ["cuda"]


def test_failed_cpu_recovery_clears_partial_model(runtime):
    runtime.fail_moves.add("cpu")
    runtime.failures = [runtime.oom("full")]
    engine = CaptionEngine(offline=True, device="cuda")
    with pytest.raises(ModelUnavailableError, match="CPU recovery failed"):
        generate(engine)
    assert engine._model is None and engine._processor is None


@pytest.mark.parametrize("device", ["auto", "gpu", "cuda:1", "", None])
def test_invalid_devices_rejected_before_loading(device):
    with pytest.raises(ValueError, match="Device"):
        CaptionEngine(device=device)


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_cli_forwards_device_to_desktop(monkeypatch, device):
    from lumacaption.cli import main

    calls = []
    monkeypatch.setattr("lumacaption.desktop.main", lambda **kw: calls.append(kw))
    assert main(["--offline", "--device", device]) == 0
    assert calls == [{"offline": True, "device": device}]


def test_cli_cuda_request_reports_cpu_fallback(runtime, tmp_path, capsys):
    from lumacaption.cli import main

    runtime.available = False
    photo = tmp_path / "photo.png"
    Image.new("RGB", (8, 8)).save(photo)
    assert main(["--offline", "--device", "cuda", str(photo)]) == 0
    output = capsys.readouterr()
    assert "CPU fallback" in output.err and "A test caption" in output.out
