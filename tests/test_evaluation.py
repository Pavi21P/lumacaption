"""Synthetic-only protocol checks; no dataset or model downloads."""

import copy
import hashlib
import json
import math
import socket

import pytest
import requests
from PIL import Image

from lumacaption import evaluate
from lumacaption.engine import ModelUnavailableError
from lumacaption.evaluation import (
    PROTOCOL,
    EvaluationError,
    build_manifest,
    exclusions_from_reports,
    identifier,
    ids_digest,
    load_manifest,
    rank,
    score,
    tokenize,
    validate_manifest,
)


def refs(text):
    return [text] * 5


def test_tokenization_is_explicit():
    assert tokenize("\uff21 Cat\u2019s DOG... isn't \uff12!") == ["a", "cat's", "dog", "isn't", "2"]


@pytest.mark.parametrize("caption", ["", "...", "a", "a cat", "a cat sits"])
def test_empty_or_short_hypothesis_has_no_smoothed_bleu4(caption):
    assert score([caption], [refs("a cat sits here")])["bleu_4"] == 0


def test_perfect_match_and_best_of_five():
    result = score(["a cat sits here"], [["x", "y", "z", "w", "a cat sits here"]])
    assert result == {"bleu_1": 100, "bleu_4": 100, "rouge_l": 100, "denominator": 1}


def test_repeated_words_are_clipped():
    result = score(["cat cat cat cat"], [refs("cat sits here now")])
    assert result["bleu_1"] == pytest.approx(25)
    assert result["bleu_4"] == 0
    assert result["rouge_l"] == 25


def test_brevity_penalty_and_closest_length_tie():
    result = score(["a cat"], [refs("a cat sits here")])
    assert result["bleu_1"] == pytest.approx(100 / math.e)
    tied = score(["a cat"], [["a", "a cat sits", "x", "y", "z"]])
    assert tied["bleu_1"] == 100


def test_corpus_precision_is_not_sentence_average_and_rouge_is_macro():
    result = score(["cat", "x x x"], [refs("cat"), refs("a b c")])
    assert result["bleu_1"] == 25
    assert result["rouge_l"] == 50


def test_failed_row_stays_in_metric_denominator():
    result = score(["a cat sits here", ""], [refs("a cat sits here")] * 2)
    assert result["denominator"] == 2
    assert result["rouge_l"] == 50
    assert result["bleu_4"] == pytest.approx(100 / math.e)


def test_lcs_respects_order_and_repetition():
    result = score(["cat dog cat"], [refs("cat cat dog")])
    assert result["rouge_l"] == pytest.approx(200 / 3)


@pytest.mark.parametrize(
    "captions,references", [([], []), (["a"], []), (["a"], [["a"]]), (["a"], [refs("")])]
)
def test_invalid_metric_inputs_rejected(captions, references):
    with pytest.raises(EvaluationError):
        score(captions, references)


@pytest.mark.parametrize(
    "name", ["../x.jpg", r"a\b.jpg", "C:x.jpg", "..", "NUL", "x.jpg ", "x\n.jpg", "x:stream"]
)
def test_invalid_identifiers_rejected(name):
    with pytest.raises(EvaluationError):
        identifier(name)


@pytest.fixture
def dataset(tmp_path):
    text = tmp_path / "text"
    images = tmp_path / "images"
    text.mkdir()
    images.mkdir()
    splits = {
        "train": ["train.jpg"],
        "dev": [f"dev{i}.png" for i in range(11)],
        "test": [f"test{i}.png" for i in range(51)],
    }
    lines = []
    for split, names in splits.items():
        (text / f"Flickr_8k.{split}Images.txt").write_text("\n".join(names), encoding="utf-8")
        for name in names:
            Image.new("RGB", (4, 4), "blue").save(images / name)
            lines.extend(f"{name}#{i}\ta blue square appears here" for i in range(5))
    (text / "Flickr8k.token.txt").write_text("\n".join(lines), encoding="utf-8")
    return text, images


@pytest.fixture
def frozen(dataset, tmp_path):
    text, images = dataset
    document = build_manifest(text, images, {"train.jpg": "Synthetic prior use"})
    path = tmp_path / "manifest.json"
    path.write_bytes(evaluate.json_bytes(document))
    return path, images, document


def test_selection_is_stable_excluded_and_frozen(dataset, tmp_path):
    text, images = dataset
    a = build_manifest(text, images, {"test0.png": "Prior tuning"})
    path = text / "Flickr_8k.testImages.txt"
    path.write_text(
        "\ufeff" + "\n".join(reversed(path.read_text().splitlines())) + "\n\n", encoding="utf-8"
    )
    b = build_manifest(text, images, {"test0.png": "Prior tuning"})
    assert a["images"] == b["images"]
    assert a["selection_sha256"] == b["selection_sha256"]
    assert "test0.png" not in {row["id"] for row in a["images"]["test"]}
    row = a["images"]["test"][0]
    assert row["image_sha256"] == hashlib.sha256((images / row["id"]).read_bytes()).hexdigest()


def test_rank_matches_documented_algorithm():
    names = ["c.jpg", "a.jpg", "b.jpg"]
    expected = sorted(
        names, key=lambda n: (hashlib.sha256(f"{PROTOCOL}|test|{n}".encode()).hexdigest(), n)
    )
    assert rank(names, "test") == expected
    assert ids_digest(["a", "b"]) == hashlib.sha256(b"a\nb\n").hexdigest()


@pytest.mark.parametrize("kind", ["duplicate", "overlap", "insufficient"])
def test_bad_splits_rejected(dataset, kind):
    text, images = dataset
    path = text / "Flickr_8k.testImages.txt"
    content = path.read_text()
    if kind == "duplicate":
        content += "\ntest0.png"
    elif kind == "overlap":
        content += "\ntrain.jpg"
    else:
        content = "test0.png"
    path.write_text(content)
    with pytest.raises(EvaluationError):
        build_manifest(text, images, {})


@pytest.mark.parametrize("kind", ["duplicate", "missing", "empty", "bad_number", "missing_tab"])
def test_bad_selected_references_rejected(dataset, kind):
    text, images = dataset
    name = rank([f"test{i}.png" for i in range(51)], "test")[0]
    path = text / "Flickr8k.token.txt"
    lines = path.read_text().splitlines()
    index = next(i for i, line in enumerate(lines) if line.startswith(name + "#0\t"))
    if kind == "duplicate":
        lines.append(lines[index])
    elif kind == "missing":
        lines.pop(index)
    elif kind == "empty":
        lines[index] = name + "#0\t "
    elif kind == "bad_number":
        lines[index] = name + "#5\tcaption"
    else:
        lines[index] = name + "#0 caption"
    path.write_text("\n".join(lines))
    with pytest.raises(EvaluationError):
        build_manifest(text, images, {})


def test_missing_input_never_resampled(dataset):
    text, images = dataset
    a = build_manifest(text, images, {})
    missing = a["images"]["test"][0]["id"]
    (images / missing).unlink()
    b = build_manifest(text, images, {})
    assert a["selection_sha256"] == b["selection_sha256"]
    assert b["images"]["test"][0]["image_sha256"] is None
    assert b["images"]["test"][0]["availability"] == "unreadable"


@pytest.mark.parametrize(
    "kind", ["version", "references", "order", "hash", "traversal", "duplicate"]
)
def test_invalid_manifest_rejected(frozen, kind):
    _, _, original = frozen
    doc = copy.deepcopy(original)
    row = doc["images"]["test"][0]
    if kind == "version":
        doc["schema_version"] = 2
    elif kind == "references":
        row["references"].pop()
    elif kind == "order":
        doc["images"]["test"].reverse()
    elif kind == "hash":
        row["image_sha256"] = "bad"
    elif kind == "traversal":
        row["id"] = "../image.png"
    else:
        doc["images"]["test"][1] = row
    with pytest.raises(EvaluationError):
        validate_manifest(doc)


def test_smoke_exclusions_validate_identifiers(tmp_path):
    p = tmp_path / "smoke.json"
    p.write_text(json.dumps({"results": [{"filename": "photo.png"}]}))
    assert exclusions_from_reports([p]) == {"photo.png": "Prior offline smoke test"}
    p.write_text(json.dumps({"results": [{"filename": "../photo.png"}]}))
    with pytest.raises(EvaluationError):
        exclusions_from_reports([p])


class FakeEngine:
    def __init__(self, *, offline, cache_dir):
        assert offline is True
        self.calls = 0

    def prepare(self):
        pass

    def caption(self, image, options):
        self.calls += 1
        assert image.mode == "RGB"
        assert options.length == "Standard" and options.beams == 3
        return "A blue square appears here"


@pytest.fixture(autouse=True)
def metadata(monkeypatch):
    monkeypatch.setattr(
        evaluate, "environment", lambda: {"git_commit": "synthetic", "git_dirty": False}
    )


def run_fake(frozen, tmp_path, engine=FakeEngine):
    path, images, _ = frozen
    return evaluate.run_evaluation(path, images, tmp_path / "run", engine_factory=engine)


def test_runner_complete_reuses_engine_and_preserves_inputs(frozen, tmp_path):
    path, images, document = frozen
    before = {r["id"]: (images / r["id"]).read_bytes() for r in document["images"]["test"]}
    instances = []

    class Engine(FakeEngine):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            instances.append(self)

    report = run_fake(frozen, tmp_path, Engine)
    assert len(instances) == 1 and instances[0].calls == 51
    assert report["baseline_complete"] and report["state"] == "completed"
    assert report["summary"]["counts"] == {"done": 50, "error": 0, "not_processed": 0}
    assert report["summary"]["metrics"]["bleu_4"] == 100
    assert report["summary"]["human_review"]["acceptable_fraction"] is None
    assert all(r["human_review"] is None for r in report["results"])
    assert report["preparation"]["status"] == report["warmup"]["status"] == "done"
    assert report["network_attempts"] == 0
    assert (tmp_path / "run/manifest.json").read_bytes() == path.read_bytes()
    assert json.loads((tmp_path / "run/report.json").read_text()) == report
    assert all((images / name).read_bytes() == content for name, content in before.items())
    template = json.loads((tmp_path / "run/review-template.json").read_text())
    assert [r["id"] for r in template["rows"]] == rank(list(before), "review")
    assert all(r["faithfulness"] is None for r in template["rows"])
    with pytest.raises(FileExistsError):
        run_fake(frozen, tmp_path)


@pytest.mark.parametrize("failure", ["missing", "changed", "corrupt"])
def test_failed_image_remains_in_report(frozen, tmp_path, failure):
    path, images, document = frozen
    target = images / document["images"]["test"][0]["id"]
    if failure == "missing":
        target.unlink()
    else:
        target.write_bytes(b"not an image")
        if failure == "corrupt":
            document["images"]["test"][0]["image_sha256"] = hashlib.sha256(
                target.read_bytes()
            ).hexdigest()
            path.write_bytes(evaluate.json_bytes(document))
    report = run_fake(frozen, tmp_path)
    assert report["summary"]["counts"] == {"done": 49, "error": 1, "not_processed": 0}
    assert report["summary"]["metrics"]["denominator"] == 50
    assert report["summary"]["metrics"]["rouge_l"] == 98
    assert report["results"][0]["generated_caption"] is None
    assert len(report["summary"]["timing"]["failed_seconds"]) == 1


@pytest.mark.parametrize("failure", ["prepare", "warmup", "fatal", "interrupt", "network", "empty"])
def test_partial_runs_and_errors_are_persisted(frozen, tmp_path, failure):
    class Engine(FakeEngine):
        def prepare(self):
            if failure == "prepare":
                raise ModelUnavailableError("private path and secret must not leak")

        def caption(self, image, options):
            if failure == "warmup":
                raise ValueError("private")
            if self.calls == 2:
                if failure == "fatal":
                    raise ModelUnavailableError("private")
                if failure == "interrupt":
                    raise KeyboardInterrupt
                if failure == "network":
                    requests.get("https://example.invalid", timeout=1)
                if failure == "empty":
                    return ""
            return super().caption(image, options)

    report = run_fake(frozen, tmp_path, Engine)
    assert len(report["results"]) == 50
    assert "private" not in json.dumps(report)
    assert report["summary"]["human_review"]["reviewed"] == 0
    if failure == "empty":
        assert report["summary"]["counts"]["error"] == 49
    else:
        assert not report["baseline_complete"]
        assert report["summary"]["counts"]["not_processed"] > 0
    if failure == "network":
        assert report["network_attempts"] == 1
    if failure == "interrupt":
        assert report["state"] == "interrupted"
    assert json.loads((tmp_path / "run/report.json").read_text()) == report


def test_network_guard_restores_environment_and_blocks_dns_http_sockets(monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "before")
    original = socket.socket.connect
    with evaluate.offline_guard() as attempts:
        for operation in (
            lambda: socket.getaddrinfo("example.invalid", 443),
            lambda: requests.get("https://example.invalid", timeout=1),
            lambda: socket.create_connection(("127.0.0.1", 9)),
        ):
            with pytest.raises(RuntimeError, match="disabled"):
                operation()
    assert len(attempts) == 3
    assert socket.socket.connect is original
    import os

    assert os.environ["HF_HUB_OFFLINE"] == "before"


def test_bad_manifest_fails_before_output_creation(frozen, tmp_path):
    path, images, _ = frozen
    path.write_text("{}")
    with pytest.raises(EvaluationError):
        evaluate.run_evaluation(path, images, tmp_path / "run")
    assert not (tmp_path / "run").exists()


def test_cli_protects_public_paths_and_existing_manifests(dataset, tmp_path, monkeypatch, capsys):
    text, images = dataset
    monkeypatch.setattr(evaluate, "PRIVATE_ROOT", tmp_path / ".local/evaluation/v1")
    output = tmp_path / ".local/evaluation/v1/manifest.json"
    args = [
        "freeze",
        "--text-root",
        str(text),
        "--image-root",
        str(images),
        "--output",
        str(output),
    ]
    assert evaluate.main(args) == 0
    assert load_manifest(output)[0]["protocol"] == PROTOCOL
    original = output.read_bytes()
    assert evaluate.main(args) == 2
    assert output.read_bytes() == original
    assert evaluate.main(args[:-1] + [str(tmp_path / "public.json")]) == 2
    assert not (tmp_path / "public.json").exists()
    assert str(tmp_path) not in capsys.readouterr().err


def test_reference_clipping_uses_maximum_not_sum():
    result = score(["cat cat cat"], [["cat"] * 5])
    assert result["bleu_1"] == pytest.approx(100 / 3)


def test_timing_uses_successful_nearest_rank_and_null_for_no_success(frozen):
    _, _, manifest = frozen
    rows = [
        {"status": "done", "elapsed_seconds": i + 1, "generated_caption": "caption"}
        for i in range(50)
    ]
    report = {"results": rows}
    evaluate.summarize(report, manifest)
    assert report["summary"]["timing"]["median_seconds"] == 25.5
    assert report["summary"]["timing"]["p95_seconds"] == 48
    for row in rows:
        row["status"] = "not_processed"
        row["elapsed_seconds"] = None
    evaluate.summarize(report, manifest)
    assert report["summary"]["timing"]["median_seconds"] is None
    assert report["summary"]["timing"]["p95_seconds"] is None
    assert report["summary"]["human_review"]["coverage"] is None


def test_image_changed_by_engine_cannot_count_as_success(frozen, tmp_path):
    _, images, document = frozen
    target = images / document["images"]["test"][0]["id"]

    class Engine(FakeEngine):
        def caption(self, image, options):
            if self.calls == 1:
                target.write_bytes(b"changed during inference")
            return super().caption(image, options)

    report = run_fake(frozen, tmp_path, Engine)
    assert report["results"][0]["status"] == "error"
    assert report["results"][0]["error"] == "input_changed_or_unreadable_at_freeze"


def test_cli_run_prints_only_aggregates(frozen, tmp_path, monkeypatch, capsys):
    path, images, manifest = frozen
    monkeypatch.setattr(evaluate, "PRIVATE_ROOT", tmp_path)
    real = evaluate.run_evaluation
    monkeypatch.setattr(
        evaluate,
        "run_evaluation",
        lambda *a, **kw: real(*a, **kw, engine_factory=FakeEngine),
    )
    assert (
        evaluate.main(
            [
                "run",
                "--manifest",
                str(path),
                "--image-root",
                str(images),
                "--output",
                str(tmp_path / "run"),
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "bleu_4" in output
    assert str(images) not in output
    assert all(row["id"] not in output for row in manifest["images"]["test"])
    assert "A blue square" not in output


@pytest.mark.parametrize("field", ["source_sha256", "split_counts", "images", "selection_sha256"])
def test_manifest_maps_cannot_be_replaced_with_key_lists(frozen, field):
    _, _, document = frozen
    document[field] = list(document[field])
    with pytest.raises(EvaluationError):
        validate_manifest(document)


def test_bleu4_nonperfect_geometric_mean():
    result = score(["a b c d e"], [refs("a b c d x")])
    # Clipped precisions: 4/5, 3/4, 2/3, 1/2; equal lengths give BP=1.
    assert result["bleu_4"] == pytest.approx(100 * (0.2**0.25))
