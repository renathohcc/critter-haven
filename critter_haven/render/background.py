"""Background do habitat. Uma única arte por planeta (assets/backgrounds/),
recortada em "cover" (preenche a janela inteira, sem barras) e ancorada
embaixo — assim a grama/chão fica sempre visível mesmo nos estados mais
baixos da janela (compact/medium), só o céu/copa das árvores é cortado."""

from __future__ import annotations

from pathlib import Path

import pygame

ASSETS_BACKGROUNDS_DIR = Path(__file__).resolve().parent.parent / "assets" / "backgrounds"

_source_cache: dict[str, pygame.Surface | None] = {}
_cropped_cache: dict[tuple[str, int, int], pygame.Surface] = {}


def _load_source(planet_id: str) -> pygame.Surface | None:
    if planet_id not in _source_cache:
        path = ASSETS_BACKGROUNDS_DIR / f"{planet_id}.png"
        _source_cache[planet_id] = (
            pygame.image.load(str(path)).convert() if path.exists() else None
        )
    return _source_cache[planet_id]


def _cover_crop(surface: pygame.Surface, target_w: int, target_h: int) -> pygame.Surface:
    src_w, src_h = surface.get_size()
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = max(1, round(src_w * scale)), max(1, round(src_h * scale))
    scaled = pygame.transform.smoothscale(surface, (new_w, new_h))
    x = (new_w - target_w) // 2
    y = new_h - target_h  # ancorado embaixo: prioriza mostrar o chao
    return scaled.subsurface(pygame.Rect(x, y, target_w, target_h)).copy()


def get_background(planet_id: str, width: int, height: int) -> pygame.Surface | None:
    """Retorna o background já recortado pro tamanho pedido, ou None se o
    planeta ainda não tem arte (o chamador cai para uma cor sólida)."""
    source = _load_source(planet_id)
    if source is None:
        return None
    key = (planet_id, width, height)
    cropped = _cropped_cache.get(key)
    if cropped is None:
        cropped = _cover_crop(source, width, height)
        _cropped_cache[key] = cropped
    return cropped
