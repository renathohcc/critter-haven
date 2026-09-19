"""Carregamento de spritesheets: uma imagem PNG (frames lado a lado) +
um JSON com os estados de animação. Ver assets/creatures/*.json para o
formato esperado.
"""

from __future__ import annotations

import json
from pathlib import Path

import pygame

ASSETS_CREATURES_DIR = Path(__file__).resolve().parent.parent / "assets" / "creatures"


class SpriteSheet:
    def __init__(self, image_path: Path, meta_path: Path) -> None:
        self.surface = pygame.image.load(str(image_path)).convert_alpha()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self.frame_width, self.frame_height = meta["frame_size"]
        self.states: dict = meta["states"]
        self._frame_cache: dict[int, pygame.Surface] = {}

    def frame(self, index: int) -> pygame.Surface:
        cached = self._frame_cache.get(index)
        if cached is None:
            rect = pygame.Rect(
                index * self.frame_width, 0, self.frame_width, self.frame_height
            )
            cached = self.surface.subsurface(rect).copy()
            self._frame_cache[index] = cached
        return cached

    def state_frames(self, state: str) -> list[pygame.Surface]:
        return [self.frame(i) for i in self.states[state]["frames"]]

    def state_fps(self, state: str) -> float:
        return self.states[state].get("fps", 6.0)

    def state_loops(self, state: str) -> bool:
        return self.states[state].get("loop", True)

    def has_state(self, state: str) -> bool:
        return state in self.states


_sheet_cache: dict[str, SpriteSheet | None] = {}


def load_creature_sheet(species_id: str) -> SpriteSheet | None:
    """Retorna None (sem lançar erro) se a criatura ainda não tem sprite —
    permite migrar espécie por espécie sem quebrar as demais, que seguem
    usando o placeholder geométrico."""
    if species_id not in _sheet_cache:
        image_path = ASSETS_CREATURES_DIR / f"{species_id}.png"
        meta_path = ASSETS_CREATURES_DIR / f"{species_id}.json"
        if image_path.exists() and meta_path.exists():
            _sheet_cache[species_id] = SpriteSheet(image_path, meta_path)
        else:
            _sheet_cache[species_id] = None
    return _sheet_cache[species_id]
