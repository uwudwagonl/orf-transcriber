"""Transcribe a media file with faster-whisper.

The model is downloaded on first use and cached under
``%APPDATA%\\OrfTranscriber\\models``. We expose segments as an iterator so the
GUI can render live progress.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from .paths import bin_dir, ffmpeg_path, models_dir


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult:
    language: str
    duration: float
    segments: list[Segment]


def _ensure_ffmpeg_on_path() -> None:
    """faster-whisper invokes ffmpeg via PATH for non-WAV inputs."""
    binary = ffmpeg_path()
    if binary.exists():
        folder = str(binary.parent)
        existing = os.environ.get("PATH", "")
        if folder not in existing.split(os.pathsep):
            os.environ["PATH"] = folder + os.pathsep + existing


def transcribe(
    media: Path,
    model_name: str = "large-v3-turbo",
    language: str = "de",
    device: str = "cpu",
    compute_type: str = "int8",
    on_segment: Callable[[Segment, float], None] | None = None,
    on_log: Callable[[str], None] | None = None,
) -> TranscriptionResult:
    """Transcribe ``media`` and return all segments.

    ``on_segment`` is called for every finalised segment with the segment and
    the fraction of audio processed (0.0–1.0), so the UI can update progress.
    """
    _ensure_ffmpeg_on_path()

    # Imported lazily so the GUI starts fast and import errors surface here.
    from faster_whisper import WhisperModel  # type: ignore

    if on_log:
        on_log(f"Lade Modell '{model_name}' ({device}/{compute_type}) …")

    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        download_root=str(models_dir()),
    )

    if on_log:
        on_log("Starte Transkription …")

    lang_arg = None if language in ("auto", "", None) else language
    segments_iter, info = model.transcribe(
        str(media),
        language=lang_arg,
        vad_filter=True,
        beam_size=5,
        condition_on_previous_text=False,
    )

    duration = float(getattr(info, "duration", 0.0)) or 0.0
    detected = getattr(info, "language", lang_arg or "und")

    collected: list[Segment] = []
    for raw in _iter_segments(segments_iter):
        seg = Segment(start=raw.start, end=raw.end, text=raw.text.strip())
        collected.append(seg)
        if on_segment:
            progress = (seg.end / duration) if duration > 0 else 0.0
            on_segment(seg, max(0.0, min(progress, 1.0)))

    return TranscriptionResult(language=detected, duration=duration, segments=collected)


def _iter_segments(it: Iterator) -> Iterator:
    """Wrap the faster-whisper iterator so caller exceptions don't leak."""
    for seg in it:
        yield seg


# Resource path used by tests and during build-time sanity checks.
def model_cache_path() -> Path:
    return models_dir()


__all__ = ["Segment", "TranscriptionResult", "transcribe", "model_cache_path"]


# Keep a reference so static analysis doesn't drop bin_dir as unused.
_ = bin_dir
