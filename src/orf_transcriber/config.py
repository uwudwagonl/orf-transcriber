"""Per-user persisted settings, stored as JSON in the AppData folder."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .paths import default_output_dir, user_data_dir


@dataclass
class Settings:
    output_dir: str = ""
    model: str = "large-v3-turbo"
    language: str = "de"
    keep_video: bool = False
    compute_type: str = "int8"
    device: str = "cpu"

    def __post_init__(self) -> None:
        if not self.output_dir:
            self.output_dir = str(default_output_dir())


def _config_path() -> Path:
    return user_data_dir() / "settings.json"


def load() -> Settings:
    path = _config_path()
    if not path.exists():
        return Settings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Settings()
    fields = {f for f in Settings.__dataclass_fields__}
    return Settings(**{k: v for k, v in data.items() if k in fields})


def save(settings: Settings) -> None:
    _config_path().write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


MODEL_CHOICES: list[tuple[str, str]] = [
    ("large-v3-turbo", "Groß (turbo) — empfohlen, ~1.5 GB"),
    ("large-v3", "Groß — beste Qualität, ~3 GB"),
    ("medium", "Mittel — schneller, ~1.5 GB"),
    ("small", "Klein — schnell, weniger genau, ~500 MB"),
]

LANGUAGE_CHOICES: list[tuple[str, str]] = [
    ("de", "Deutsch"),
    ("auto", "Automatisch erkennen"),
    ("en", "Englisch"),
]
