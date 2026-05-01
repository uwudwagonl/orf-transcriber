"""Locate bundled binaries (orfondl, ffmpeg) and per-user data directories.

Works both when running from source (during development) and when frozen by
PyInstaller. Bundled binaries live in a ``bin`` folder next to the executable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from . import APP_NAME


def _frozen_root() -> Path | None:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return None


def app_root() -> Path:
    frozen = _frozen_root()
    if frozen is not None:
        return frozen
    return Path(__file__).resolve().parents[2]


def bin_dir() -> Path:
    frozen = _frozen_root()
    if frozen is not None:
        return frozen / "bin"
    return app_root() / "build" / "vendor"


def _exe(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def orfondl_path() -> Path:
    return bin_dir() / _exe("orfondl")


def ffmpeg_path() -> Path:
    return bin_dir() / _exe("ffmpeg")


def ffprobe_path() -> Path:
    return bin_dir() / _exe("ffprobe")


def user_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    folder = base / APP_NAME.replace(" ", "")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def models_dir() -> Path:
    folder = user_data_dir() / "models"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def default_output_dir() -> Path:
    if os.name == "nt":
        candidates = [Path.home() / "Documents", Path.home() / "OneDrive" / "Documents"]
    else:
        candidates = [Path.home() / "Documents"]
    base = next((c for c in candidates if c.exists()), Path.home())
    folder = base / "ORF Transkripte"
    folder.mkdir(parents=True, exist_ok=True)
    return folder
