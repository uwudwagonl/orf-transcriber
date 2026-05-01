"""Background pipeline: download → transcribe → write Word doc.

Runs in its own thread; communicates progress via a thread-safe queue of
``Event`` objects that the GUI polls with ``after``.
"""

from __future__ import annotations

import queue
import tempfile
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path

from . import config, metadata
from .config import Settings
from .docx_writer import write_transcript
from .downloader import download
from .metadata import VideoMeta
from .transcriber import Segment, transcribe


@dataclass
class Event:
    kind: str
    message: str = ""
    progress: float | None = None
    payload: object | None = None


class Job(threading.Thread):
    def __init__(self, url: str, settings: Settings, events: queue.Queue[Event]) -> None:
        super().__init__(daemon=True)
        self.url = url.strip()
        self.settings = settings
        self.events = events
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def _emit(self, kind: str, message: str = "", **kw: object) -> None:
        self.events.put(Event(kind=kind, message=message, **kw))

    def _check_cancel(self) -> None:
        if self._cancel.is_set():
            raise RuntimeError("Vom Benutzer abgebrochen.")

    def run(self) -> None:
        try:
            self._run()
        except Exception as exc:  # noqa: BLE001
            self._emit("error", str(exc), payload=traceback.format_exc())

    def _run(self) -> None:
        self._emit("status", "Lade Video-Informationen …", progress=0.02)
        meta = metadata.fetch(self.url)
        self._emit("log", f"Titel: {meta.title}")

        out_dir = Path(self.settings.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        base = metadata.safe_filename(meta.title)
        video_path = out_dir / f"{base}.mp4"
        docx_path = out_dir / f"{base}.docx"

        # ── download ────────────────────────────────────────────────────
        self._check_cancel()
        self._emit("status", "Lade Video herunter …", progress=0.05)
        with tempfile.TemporaryDirectory(prefix="orf-dl-") as tmpdir:
            scratch = Path(tmpdir) / f"{base}.mp4"
            download(self.url, scratch, on_log=lambda s: self._emit("log", s))
            self._check_cancel()

            # If user wants to keep the video, copy it to output folder.
            target_video: Path | None = None
            if self.settings.keep_video:
                scratch.replace(video_path)
                target_video = video_path
                source_for_transcribe = video_path
            else:
                source_for_transcribe = scratch

            # ── transcribe ─────────────────────────────────────────────
            self._emit("status", "Transkribiere Audio …", progress=0.35)

            def on_segment(seg: Segment, frac: float) -> None:
                self._check_cancel()
                # map 0..1 of audio to 0.35..0.95 of overall progress
                overall = 0.35 + 0.60 * frac
                self._emit(
                    "segment",
                    seg.text,
                    progress=overall,
                    payload=seg,
                )

            result = transcribe(
                source_for_transcribe,
                model_name=self.settings.model,
                language=self.settings.language,
                device=self.settings.device,
                compute_type=self.settings.compute_type,
                on_segment=on_segment,
                on_log=lambda s: self._emit("log", s),
            )

            self._check_cancel()

            # ── write Word doc ─────────────────────────────────────────
            self._emit("status", "Erstelle Word-Dokument …", progress=0.97)
            write_transcript(
                output_path=docx_path,
                meta=meta,
                result=result,
                source_url=self.url,
                video_file=target_video,
            )

        self._emit(
            "done",
            "Fertig! Transkript gespeichert.",
            progress=1.0,
            payload={"docx": str(docx_path), "video": str(video_path) if self.settings.keep_video else None},
        )


__all__ = ["Job", "Event", "config", "VideoMeta"]
