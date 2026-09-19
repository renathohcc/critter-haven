"""Cache de fontes. Criar uma pygame.font.SysFont nova a cada frame faz
lookup no sistema operacional e é caro — pesava sozinho boa parte da
CPU do overlay rodando parado (Fase 7)."""

from __future__ import annotations

import pygame

_cache: dict[tuple[str, int, bool], pygame.font.Font] = {}


def get_font(name: str, size: int, bold: bool = False) -> pygame.font.Font:
    key = (name, size, bold)
    font = _cache.get(key)
    if font is None:
        font = pygame.font.SysFont(name, size, bold=bold)
        _cache[key] = font
    return font
