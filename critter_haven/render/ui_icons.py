"""Botões de ícone da HUD (Baú, Upgrades, Nave, Álbum, Vender Tudo).
Carregados uma vez e reescalados com cache — a arte original vem em
~50-170px, mas a barra overlay precisa deles bem menores."""

from __future__ import annotations

from pathlib import Path

import pygame

ASSETS_UI_DIR = Path(__file__).resolve().parent.parent / "assets" / "ui"

_source_cache: dict[str, pygame.Surface] = {}
_scaled_cache: dict[tuple[str, int], pygame.Surface] = {}


def _load_source(name: str) -> pygame.Surface:
    if name not in _source_cache:
        path = ASSETS_UI_DIR / f"{name}.png"
        _source_cache[name] = pygame.image.load(str(path)).convert_alpha()
    return _source_cache[name]


def get_button(name: str, target_height: int) -> pygame.Surface:
    """Retorna o botão `name` (sem extensão, ex: "btn_bau") escalado pra
    `target_height` de altura, mantendo a proporção original."""
    key = (name, target_height)
    if key not in _scaled_cache:
        source = _load_source(name)
        scale = target_height / source.get_height()
        target_width = max(1, round(source.get_width() * scale))
        _scaled_cache[key] = pygame.transform.smoothscale(
            source, (target_width, target_height)
        )
    return _scaled_cache[key]
