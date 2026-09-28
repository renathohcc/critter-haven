"""Barra de energia (progresso até o próximo spawn) em pixel art: uma
moldura de metal/madeira (3 fatias: ponta esquerda/meio esticável/ponta
direita, geradas no Aseprite) com um "líquido" dourado que enche por
dentro conforme a energia do habitat sobe, e um brilho pulsante quando
está quase cheia (prestes a spawnar).

A moldura tem um buraco central transparente — o líquido é desenhado
primeiro (no fundo), a moldura é blitada por cima, e o buraco revela o
líquido exatamente encaixado dentro do vidro/metal. Tudo é composto na
resolução nativa da arte (altura 32) e só then escalado (nearest-
neighbor) pro tamanho de exibição, pra manter a nitidez pixel-art.
"""

from __future__ import annotations

import math
from pathlib import Path

import pygame

ASSETS_UI_DIR = Path(__file__).resolve().parent.parent / "assets" / "ui"

NATIVE_HEIGHT = 32
NATIVE_BORDER = 4  # espessura da moldura (ver energy_bar_full.aseprite)
CAP_WIDTH = 20

TRACK_COLOR = (26, 20, 16)
LIQUID_STOPS = (
    (255, 248, 210),  # brilho no topo (superficie do liquido)
    (255, 214, 92),  # cor principal (mesma do ENERGY_BAR_COLOR antigo)
    (224, 156, 40),  # meio-sombra
    (168, 100, 18),  # fundo, mais escuro
)
GLOW_COLOR = (255, 220, 120)

_cap_left_src: pygame.Surface | None = None
_cap_right_src: pygame.Surface | None = None
_mid_src: pygame.Surface | None = None
_frame_cache: dict[int, pygame.Surface] = {}
_liquid_gradient_cache: dict[int, pygame.Surface] = {}
_glow_cache: dict[tuple[int, int], pygame.Surface] = {}


def _load_sources() -> None:
    global _cap_left_src, _cap_right_src, _mid_src
    if _cap_left_src is None:
        _cap_left_src = pygame.image.load(
            str(ASSETS_UI_DIR / "energy_bar_cap_left.png")
        ).convert_alpha()
        _cap_right_src = pygame.image.load(
            str(ASSETS_UI_DIR / "energy_bar_cap_right.png")
        ).convert_alpha()
        _mid_src = pygame.image.load(str(ASSETS_UI_DIR / "energy_bar_mid.png")).convert_alpha()


def _get_frame(native_width: int) -> pygame.Surface:
    """Moldura completa (ponta+meio esticado+ponta) na largura nativa
    pedida, com buraco central transparente. Cacheada por largura."""
    _load_sources()
    if native_width not in _frame_cache:
        frame = pygame.Surface((native_width, NATIVE_HEIGHT), pygame.SRCALPHA)
        frame.blit(_cap_left_src, (0, 0))
        frame.blit(_cap_right_src, (native_width - CAP_WIDTH, 0))
        mid_width = max(0, native_width - 2 * CAP_WIDTH)
        if mid_width > 0:
            mid = pygame.transform.scale(_mid_src, (mid_width, NATIVE_HEIGHT))
            frame.blit(mid, (CAP_WIDTH, 0))
        _frame_cache[native_width] = frame
    return _frame_cache[native_width]


def _get_liquid_gradient(height: int) -> pygame.Surface:
    """Textura de 1px de largura com o gradiente vertical do líquido
    (brilho no topo, sombra no fundo) — esticada horizontalmente depois
    conforme a quantidade de líquido a desenhar."""
    if height not in _liquid_gradient_cache:
        grad = pygame.Surface((1, height), pygame.SRCALPHA)
        stops = LIQUID_STOPS
        segments = len(stops) - 1
        for y in range(height):
            t = y / max(1, height - 1)
            seg_f = t * segments
            seg = min(int(seg_f), segments - 1)
            local_t = seg_f - seg
            c0, c1 = stops[seg], stops[seg + 1]
            color = tuple(round(c0[i] + (c1[i] - c0[i]) * local_t) for i in range(3))
            grad.set_at((0, y), (*color, 255))
        _liquid_gradient_cache[height] = grad
    return _liquid_gradient_cache[height]


def _get_glow(native_width: int, native_height: int) -> pygame.Surface:
    key = (native_width, native_height)
    if key not in _glow_cache:
        pad = 10
        glow = pygame.Surface(
            (native_width + pad * 2, native_height + pad * 2), pygame.SRCALPHA
        )
        # aneis concentricos com alpha decrescente pra simular um brilho
        # suave (halo) ao redor da barra, sem depender de blur de verdade.
        rings = 5
        for i in range(rings, 0, -1):
            inset = -int(pad * i / rings)
            rect = pygame.Rect(
                pad + inset, pad + inset,
                native_width - 2 * inset, native_height - 2 * inset,
            )
            alpha = int(70 * (1 - i / (rings + 1)))
            surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(
                surf, (*GLOW_COLOR, alpha), surf.get_rect(),
                border_radius=rect.height // 2,
            )
            glow.blit(surf, rect.topleft)
        _glow_cache[key] = glow
    return _glow_cache[key]


def draw_energy_bar(
    surface: pygame.Surface,
    x: int,
    y: int,
    display_width: int,
    display_height: int,
    ratio: float,
    time_elapsed: float,
) -> None:
    """Desenha a barra de energia (moldura pixel art + líquido dourado +
    brilho) em `surface`, ancorada em (x, y) com o tamanho de exibição
    dado. `ratio` é a energia atual (0-1). `time_elapsed` (segundos
    corridos) anima o brilho pulsante quando a barra está quase cheia."""
    ratio = max(0.0, min(1.0, ratio))
    native_width = max(2 * CAP_WIDTH + 4, round(display_width * NATIVE_HEIGHT / display_height))
    native_height = NATIVE_HEIGHT

    bar = pygame.Surface((native_width, native_height), pygame.SRCALPHA)

    hole = pygame.Rect(
        NATIVE_BORDER, NATIVE_BORDER,
        native_width - 2 * NATIVE_BORDER, native_height - 2 * NATIVE_BORDER,
    )
    pygame.draw.rect(bar, TRACK_COLOR, hole, border_radius=hole.height // 2)

    liquid_width = int(hole.width * ratio)
    if liquid_width > 0:
        liquid_rect = pygame.Rect(hole.x, hole.y, liquid_width, hole.height)
        gradient = _get_liquid_gradient(hole.height)
        stretched = pygame.transform.scale(gradient, (liquid_width, hole.height))
        # a moldura ainda vai cortar as pontas arredondadas por cima, mas
        # aqui já aproximamos os cantos do liquido pra nao vazar reto por
        # baixo do buraco redondo quando a barra esta quase vazia/cheia.
        mask = pygame.Surface(liquid_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            mask, (255, 255, 255, 255), mask.get_rect(), border_radius=hole.height // 2
        )
        stretched.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        bar.blit(stretched, liquid_rect.topleft)

        # meniscos: uma linha vertical mais clara na borda direita do
        # liquido, sugerindo o vidro/liquido reagindo a luz.
        if liquid_width < hole.width:
            edge_x = hole.x + liquid_width - 1
            pygame.draw.line(
                bar, (255, 250, 225), (edge_x, hole.y + 2), (edge_x, hole.y + hole.height - 3)
            )

    frame = _get_frame(native_width)
    bar.blit(frame, (0, 0))

    scaled = pygame.transform.scale(bar, (display_width, display_height))

    if ratio > 0.85:
        pulse = 0.5 + 0.5 * math.sin(time_elapsed * 6.0)
        near_full = (ratio - 0.85) / 0.15
        glow_alpha = int(90 * near_full * (0.5 + 0.5 * pulse))
        if glow_alpha > 0:
            glow = _get_glow(display_width, display_height).copy()
            glow.set_alpha(glow_alpha)
            surface.blit(glow, (x - 10, y - 10))

    surface.blit(scaled, (x, y))
