"""Lazy-loaded, local BLIP inference. No input image leaves this process."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .config import LENGTHS as LENGTHS
from .config import MODEL_ID as MODEL_ID
from .config import MODEL_REVISION as MODEL_REVISION
from .config import default_cache as default_cache

DEVICES = ("cpu", "cuda")


class ModelUnavailableError(RuntimeError):
    """Model setup failed; the user can retry after fixing the environment."""


@dataclass(frozen=True)
class CaptionOptions:
    length: str = "Standard"
    beams: int = 3

    def __post_init__(self) -> None:
        if self.length not in LENGTHS:
            raise ValueError(f"Length must be one of: {', '.join(LENGTHS)}")
        if not 1 <= self.beams <= 5:
            raise ValueError("Beam count must be between 1 and 5.")


class CaptionEngine:
    """One engine per worker; models are reused across images and batches."""

    def __init__(
        self, *, offline: bool = False, cache_dir: Path | None = None, device: str = "cpu"
    ) -> None:
        if device not in DEVICES:
            raise ValueError(f"Device must be one of: {', '.join(DEVICES)}")
        self.requested_device = device
        self.device = "cpu"
        self.fallback_reason = ""
        self._status: Callable[[str], None] = lambda _: None
        self.offline = offline
        self.cache_dir = cache_dir or default_cache()
        self._model = None
        self._processor = None

    def prepare(self, status: Callable[[str], None] | None = None) -> None:
        if status is not None:
            self._status = status
        if self._model is not None:
            if status is not None:
                self._report_device()
            return
        self._status(
            "Loading local model..."
            if self.offline
            else "Loading AI model (first use downloads about 1 GB)..."
        )
        try:
            import truststore

            truststore.inject_into_ssl()
            os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
            # Load the pinned official weights without launching the optional
            # remote conversion worker, which can keep the process alive on exit.
            os.environ["DISABLE_SAFETENSORS_CONVERSION"] = "true"
            import torch
            from transformers import BlipForConditionalGeneration, BlipProcessor

            torch.set_num_threads(min(4, os.cpu_count() or 1))
            shared = {
                "revision": MODEL_REVISION,
                "cache_dir": str(self.cache_dir),
                "local_files_only": self.offline,
                "token": False,
            }
            processor = BlipProcessor.from_pretrained(MODEL_ID, **shared, use_fast=False)
            # The pinned official checkpoint supplies .bin weights. torch >=2.6
            # and restricted weights-only loading avoid arbitrary pickle objects.
            model = BlipForConditionalGeneration.from_pretrained(
                MODEL_ID, **shared, use_safetensors=False, weights_only=True
            )
            self.device = "cpu"
            self.fallback_reason = ""
            if self.requested_device == "cuda":
                try:
                    available = torch.cuda.is_available()
                except (RuntimeError, AssertionError):
                    available = False
                if available:
                    self.device = "cuda"
                else:
                    self.fallback_reason = "CUDA is unavailable in this environment."
            try:
                model.to(self.device)
            except (RuntimeError, AssertionError):
                if self.device != "cuda":
                    raise
                model.to("cpu")
                self.device = "cpu"
                self.fallback_reason = "The model could not be moved to CUDA."
            model.eval()
            self._processor = processor
            self._model = model
        except Exception as exc:
            self._model = None
            self._processor = None
            hint = (
                "The cached model is missing or incomplete. Turn off Offline mode "
                "and connect to the internet once."
                if self.offline
                else "Check your internet connection and free disk space, then retry. "
                "If dependencies are missing, run Setup-Windows.ps1."
            )
            raise ModelUnavailableError(f"Unable to load the captioning model. {hint}") from exc
        self._report_device()

    def _report_device(self) -> None:
        message = f"Model ready - captions run locally on {self.device.upper()}."
        if self.fallback_reason:
            message += f" CPU fallback: {self.fallback_reason}"
        self._status(message)

    def caption(self, image: Image.Image, options: CaptionOptions) -> str:
        self.prepare()
        import torch

        try:
            output = self._generate(image, options)
        except torch.cuda.OutOfMemoryError:
            if self.device != "cuda":
                raise
            # Leave the exception scope before retrying, releasing failed-call tensors.
            output = None
        if output is None:
            try:
                self._model.to("cpu")
            except (RuntimeError, AssertionError) as exc:
                self._model = None
                self._processor = None
                raise ModelUnavailableError(
                    "CUDA ran out of memory and CPU recovery failed. Select CPU and retry."
                ) from exc
            self.device = "cpu"
            self.fallback_reason = "CUDA ran out of memory; retried once on CPU."
            self._report_device()
            output = self._generate(image, options)
        caption = self._processor.decode(output[0], skip_special_tokens=True).strip()
        if not caption:
            raise RuntimeError("The model returned an empty caption. Try another image.")
        return caption[0].upper() + caption[1:]

    def _generate(self, image: Image.Image, options: CaptionOptions):
        import torch

        inputs = self._processor(images=image, return_tensors="pt")
        inputs = {name: tensor.to(self.device) for name, tensor in inputs.items()}
        with torch.inference_mode():
            return self._model.generate(
                **inputs,
                max_new_tokens=LENGTHS[options.length],
                num_beams=options.beams,
                do_sample=False,
                no_repeat_ngram_size=3,
            )
