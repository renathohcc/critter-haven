"""Balão de dica do tutorial + destaque pulsante no alvo da ação."""

from __future__ import annotations

import math

import pygame

from critter_haven.render.fonts import get_font

BALLOON_BG = (26, 20, 16, 235)
BALLOON_BORDER = (244, 214, 147)
TEXT_COLOR = (230, 214, 178)
SKIP_COLOR = (150, 135, 110)
HIGHLIGHT_COLOR = (255, 232, 150)


def _wrap(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def draw_hint(
    surface: pygame.Surface,
    text: str,
    top_left: tuple[int, int],
    max_width: int,
    skip_label: str = "Pular tutorial",
) -> pygame.Rect:
    """Desenha o balão e devolve o Rect do link "Pular" (pra detectar clique)."""
    font = get_font("consolas", 14)
    small = get_font("consolas", 11)
    lines = _wrap(text, font, max_width - 24)
    line_h = font.get_height() + 2
    width = max(font.size(line)[0] for line in lines) + 24
    height = len(lines) * line_h + 36
    rect = pygame.Rect(top_left, (width, height))

    balloon = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(balloon, BALLOON_BG, balloon.get_rect(), border_radius=10)
    pygame.draw.rect(balloon, BALLOON_BORDER, balloon.get_rect(), width=2, border_radius=10)
    surface.blit(balloon, rect.topleft)

    for i, line in enumerate(lines):
        surface.blit(font.render(line, True, TEXT_COLOR), (rect.x + 12, rect.y + 8 + i * line_h))
    skip = small.render(skip_label, True, SKIP_COLOR)
    skip_rect = skip.get_rect(bottomright=(rect.right - 12, rect.bottom - 6))
    surface.blit(skip, skip_rect)
    return skip_rect


def draw_highlight(surface: pygame.Surface, rect: pygame.Rect, time_elapsed: float, round_: bool = False) -> None:
    pulse = 0.5 + 0.5 * math.sin(time_elapsed * 5.0)
    grow = int(3 + 3 * pulse)
    box = rect.inflate(grow * 2, grow * 2)
    alpha = int(140 + 115 * pulse)
    overlay = pygame.Surface(box.size, pygame.SRCALPHA)
    color = (*HIGHLIGHT_COLOR, alpha)
    if round_:
        pygame.draw.ellipse(overlay, color, overlay.get_rect(), width=3)
    else:
        pygame.draw.rect(overlay, color, overlay.get_rect(), width=3, border_radius=8)
    surface.blit(overlay, box.topleft)
