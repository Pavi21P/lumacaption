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

    def __init__(self, *, offline: bool = False, cache_dir: Path | None = None) -> None:
        self.offline = offline
        self.cache_dir = cache_dir or default_cache()
        self._model = None
        self._processor = None

    def prepare(self, status: Callable[[str], None] = lambda _: None) -> None:
        if self._model is not None:
            return
        status(
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
            model.to("cpu")
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
        status("Model ready — captions run locally on your CPU.")

    def caption(self, image: Image.Image, options: CaptionOptions) -> str:
        self.prepare()
        import torch

        inputs = self._processor(images=image, return_tensors="pt")
        with torch.inference_mode():
            output = self._model.generate(
                **inputs,
                max_new_tokens=LENGTHS[options.length],
                num_beams=options.beams,
                do_sample=False,
                no_repeat_ngram_size=3,
            )
        caption = self._processor.decode(output[0], skip_special_tokens=True).strip()
        if not caption:
            raise RuntimeError("The model returned an empty caption. Try another image.")
        return caption[0].upper() + caption[1:]
