"""Desenho das criaturas. Usa sprite real (spritesheet + animação) se a
espécie já tiver assets em assets/creatures/; caso contrário cai no
placeholder geométrico — permite trocar espécie por espécie sem quebrar
as demais nem tocar em lógica de jogo."""

from __future__ import annotations

import pygame

from critter_haven.entities.creature import Creature
from critter_haven.render.animation import current_frame
from critter_haven.render.fonts import get_font
from critter_haven.render.spritesheet import load_creature_sheet

RADIUS = 20

_SPECIES_COLOR = {
    "mossnib": (107, 142, 74),
    "pebblit": (150, 130, 110),
    "lumibloom": (230, 200, 90),
    "breezel": (150, 190, 230),
    "solarva": (255, 170, 40),
}

_RARITY_RING = {
    "common": None,
    "rare": (90, 170, 255),
    "special": (255, 215, 0),
}


def _animation_state_for(creature: Creature) -> str:
    if creature.is_clicked_feedback_active():
        return "click"
    return "walk"


def draw_creature(surface: pygame.Surface, creature: Creature, dt: float = 0.0) -> None:
    pos = (int(creature.x), int(creature.y))
    sheet = load_creature_sheet(creature.species.id)

    if sheet is not None:
        state = _animation_state_for(creature)
        frame = current_frame(creature, sheet, state, dt)
        rect = frame.get_rect(center=pos)
        surface.blit(frame, rect)
    else:
        _draw_placeholder(surface, creature, pos)

    ring_color = _RARITY_RING.get(creature.rarity)
    if ring_color:
        pygame.draw.circle(surface, ring_color, pos, RADIUS + 3, width=3)

    font = get_font("consolas", 12)
    label = font.render(creature.species.name, True, (255, 255, 255))
    surface.blit(label, (pos[0] - label.get_width() // 2, pos[1] + RADIUS + 4))


def _draw_placeholder(
    surface: pygame.Surface, creature: Creature, pos: tuple[int, int]
) -> None:
    color = _SPECIES_COLOR.get(creature.species.id, (200, 200, 200))

    if creature.is_clicked_feedback_active():
        pygame.draw.circle(surface, (255, 255, 255), pos, RADIUS + 6, width=2)

    pygame.draw.circle(surface, color, pos, RADIUS)
