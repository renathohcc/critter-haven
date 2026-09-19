"""Habitat com profundidade de verdade: várias camadas paralaxe (céu,
matas ao fundo, linha de árvores), uma faixa de chão texturizada e
decoração de primeiro plano desenhada NA FRENTE das criaturas — é essa
última parte que dá a sensação de "dentro do cenário" em vez de
"colado num papel de parede" (feedback do dev).

Assets de terceiros (GandalfHardcore, itch.io) sob licença de uso
comercial em jogos — ver assets/backgrounds/elyndor/ para a origem.
"""

from __future__ import annotations

from pathlib import Path

import pygame

ASSETS_BACKGROUNDS_DIR = Path(__file__).resolve().parent.parent / "assets" / "backgrounds"

GROUND_BAND_HEIGHT = 28
GROUND_DIRT_COLOR = (34, 31, 25)

# ordem de fundo pra frente (paralaxe): sky é o mais distante
_PARALLAX_LAYERS = (
    "layer5_sky.png",
    "layer4_far.png",
    "layer3_mid.png",
    "layer2_near.png",
    "layer1_treeline.png",
)

# (arquivo, x relativo à largura da janela [0-1], escala)
_FOREGROUND_DECOR = (
    ("deco_birch.png", 0.06, 1.0),
    ("deco_bush_big.png", 0.30, 1.0),
    ("deco_tuft.png", 0.55, 1.0),
    ("deco_bush_big.png", 0.80, 0.85),
    ("deco_tuft.png", 0.93, 1.0),
)

_image_cache: dict[str, pygame.Surface | None] = {}
_composed_cache: dict[tuple[str, int, int], pygame.Surface | None] = {}
_decor_cache: dict[tuple[str, int, int], list[tuple[pygame.Surface, tuple[int, int]]]] = {}


def _load(planet_id: str, filename: str) -> pygame.Surface | None:
    key = f"{planet_id}/{filename}"
    if key not in _image_cache:
        path = ASSETS_BACKGROUNDS_DIR / planet_id / filename
        _image_cache[key] = pygame.image.load(str(path)).convert_alpha() if path.exists() else None
    return _image_cache[key]


def _cover_crop(surface: pygame.Surface, target_w: int, target_h: int) -> pygame.Surface:
    src_w, src_h = surface.get_size()
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = max(1, round(src_w * scale)), max(1, round(src_h * scale))
    scaled = pygame.transform.smoothscale(surface, (new_w, new_h))
    x = (new_w - target_w) // 2
    y = new_h - target_h  # ancorado embaixo: prioriza mostrar o chao
    return scaled.subsurface(pygame.Rect(x, y, target_w, target_h)).copy()


def _compose(planet_id: str, width: int, height: int) -> pygame.Surface | None:
    first = _load(planet_id, _PARALLAX_LAYERS[0])
    if first is None:
        return None

    composed = pygame.Surface((width, height), pygame.SRCALPHA)
    for filename in _PARALLAX_LAYERS:
        layer = _load(planet_id, filename)
        if layer is not None:
            composed.blit(_cover_crop(layer, width, height), (0, 0))

    ground_y = height - GROUND_BAND_HEIGHT
    pygame.draw.rect(
        composed, GROUND_DIRT_COLOR, pygame.Rect(0, ground_y, width, GROUND_BAND_HEIGHT)
    )
    grass_cap = _load(planet_id, "ground_cap.png")
    if grass_cap is not None:
        cap_scale = 2  # pixels pequenos demais ficam ilegiveis em 900px de largura
        cap = pygame.transform.scale(
            grass_cap, (grass_cap.get_width() * cap_scale, grass_cap.get_height() * cap_scale)
        )
        x = 0
        while x < width:
            composed.blit(cap, (x, ground_y))
            x += cap.get_width()

    return composed


def get_background(planet_id: str, width: int, height: int) -> pygame.Surface | None:
    """Camadas de fundo + chão. Desenhar ANTES das criaturas."""
    key = (planet_id, width, height)
    if key not in _composed_cache:
        _composed_cache[key] = _compose(planet_id, width, height)
    return _composed_cache[key]


def get_foreground_decor(
    planet_id: str, width: int, height: int
) -> list[tuple[pygame.Surface, tuple[int, int]]]:
    """Elementos de decoração (arbustos, árvores) já posicionados, prontos
    pra blit. Desenhar DEPOIS das criaturas — é isso que cria a sensação
    de profundidade real (a criatura passa "atrás" do arbusto)."""
    key = (planet_id, width, height)
    if key not in _decor_cache:
        ground_y = height - GROUND_BAND_HEIGHT
        placed = []
        for filename, rel_x, scale in _FOREGROUND_DECOR:
            image = _load(planet_id, filename)
            if image is None:
                continue
            if scale != 1.0:
                w, h = image.get_size()
                image = pygame.transform.smoothscale(
                    image, (max(1, round(w * scale)), max(1, round(h * scale)))
                )
            x = round(width * rel_x - image.get_width() / 2)
            y = ground_y - image.get_height() + 6  # afunda um pouco no chao
            placed.append((image, (x, y)))
        _decor_cache[key] = placed
    return _decor_cache[key]
