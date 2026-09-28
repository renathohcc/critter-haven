""""Selos" (badges) compactos pra exibir ouro/criaturas/baú na HUD: um
ícone pixel art + texto dentro de uma pilula escura semi-transparente,
em vez de texto solto flutuando sobre o cenário (baixo contraste e mais
"poluído" visualmente). Mesma paleta escura/dourada do resto da UI."""

from __future__ import annotations

from pathlib import Path

import pygame

from critter_haven.render.fonts import get_font

ASSETS_UI_DIR = Path(__file__).resolve().parent.parent / "assets" / "ui"

BADGE_BG = (26, 20, 16, 195)
BADGE_BORDER = (9, 2, 2, 230)
TEXT_GOLD = (244, 214, 147)
TEXT_DIM = (200, 185, 160)

_icon_source_cache: dict[str, pygame.Surface] = {}
_icon_scaled_cache: dict[tuple[str, int], pygame.Surface] = {}


def _get_icon(name: str, height: int) -> pygame.Surface:
    key = (name, height)
    if key not in _icon_scaled_cache:
        if name not in _icon_source_cache:
            path = ASSETS_UI_DIR / f"{name}.png"
            _icon_source_cache[name] = pygame.image.load(str(path)).convert_alpha()
        source = _icon_source_cache[name]
        scale = height / source.get_height()
        width = max(1, round(source.get_width() * scale))
        _icon_scaled_cache[key] = pygame.transform.scale(source, (width, height))
    return _icon_scaled_cache[key]


def draw_stat_badge(
    surface: pygame.Surface,
    x: int,
    y: int,
    icon_name: str,
    text: str,
    *,
    icon_height: int = 20,
    text_color: tuple[int, int, int] = TEXT_GOLD,
    font_size: int = 14,
    align: str = "left",
) -> pygame.Rect:
    """Desenha o selo com âncora em (x, y) e retorna o Rect ocupado.
    `align` == "right" ancora pelo canto superior direito (x é a borda
    direita) — útil pra empilhar selos alinhados à direita da tela."""
    icon = _get_icon(icon_name, icon_height)
    font = get_font("consolas", font_size, bold=True)
    text_surf = font.render(text, True, text_color)

    pad_x, pad_y, gap = 8, 5, 6
    content_h = max(icon_height, text_surf.get_height())
    width = pad_x * 2 + icon.get_width() + gap + text_surf.get_width()
    height = pad_y * 2 + content_h

    if align == "right":
        rect = pygame.Rect(x - width, y, width, height)
    else:
        rect = pygame.Rect(x, y, width, height)

    badge = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(badge, BADGE_BG, badge.get_rect(), border_radius=height // 2)
    pygame.draw.rect(
        badge, BADGE_BORDER, badge.get_rect(), width=2, border_radius=height // 2
    )
    icon_y = (height - icon.get_height()) // 2
    badge.blit(icon, (pad_x, icon_y))
    text_y = (height - text_surf.get_height()) // 2
    badge.blit(text_surf, (pad_x + icon.get_width() + gap, text_y))

    surface.blit(badge, rect.topleft)
    return rect
