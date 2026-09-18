"""Leitura/escrita do arquivo de save em JSON, com tratamento de
arquivo corrompido ou inexistente (GDD 6.11)."""

from __future__ import annotations

import json
from pathlib import Path

SAVE_DIR = Path("saves")
SAVE_PATH = SAVE_DIR / "save.json"


def save_game(data: dict, path: Path = SAVE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(path)


def load_game(path: Path = SAVE_PATH) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or "version" not in data:
        return None
    return data
