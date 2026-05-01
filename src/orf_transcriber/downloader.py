"""Wrapper around the bundled ``orfondl`` binary."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from .paths import orfondl_path


class DownloadError(RuntimeError):
    pass


def _creationflags() -> int:
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def download(
    url: str,
    output_path: Path,
    on_log: Callable[[str], None] | None = None,
) -> Path:
    """Download a single ORF ON video to ``output_path`` (must end in .mp4)."""
    if output_path.suffix.lower() != ".mp4":
        raise DownloadError("Output path must end in .mp4")

    binary = orfondl_path()
    if not binary.exists():
        raise DownloadError(f"orfondl-Programm nicht gefunden: {binary}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if on_log:
        on_log(f"Starte Download: {url}")

    process = subprocess.Popen(
        [str(binary), url, str(output_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_creationflags(),
        cwd=str(output_path.parent),
    )

    assert process.stdout is not None
    for line in process.stdout:
        line = line.rstrip()
        if line and on_log:
            on_log(line)

    rc = process.wait()
    if rc != 0:
        raise DownloadError(f"orfondl wurde mit Code {rc} beendet")

    if not output_path.exists():
        raise DownloadError("Download abgeschlossen, aber Datei wurde nicht gefunden.")

    return output_path
