"""Desenho das criaturas. Usa sprite real (spritesheet + animação) se a
espécie já tiver assets em assets/creatures/; caso contrário cai no
placeholder geométrico — permite trocar espécie por espécie sem quebrar
as demais nem tocar em lógica de jogo.

A animação (respiração, caminhada, carinho, soltar item) vem dos frames
do próprio sprite. O placeholder geométrico não tem frames, então segue
estático."""

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


def _animation_state_for(creature: Creature, sheet) -> str:
    if creature.is_clicked_feedback_active() and sheet.has_state("click"):
        return "click"
    if creature.is_item_feedback_active() and sheet.has_state("item"):
        return "item"
    if creature.is_walking:
        desired = "walk_left" if creature.direction < 0 else "walk_right"
        if sheet.has_state(desired):
            return desired
        if sheet.has_state("walk"):
            return "walk"
    if sheet.has_state("idle"):
        return "idle"
    fallback = "walk_left" if creature.direction < 0 else "walk_right"
    return fallback if sheet.has_state(fallback) else next(iter(sheet.states))


def draw_creature(surface: pygame.Surface, creature: Creature, dt: float = 0.0) -> None:
    pos = (int(creature.x), int(creature.y))
    sheet = load_creature_sheet(creature.species.id)

    if sheet is not None:
        frame = current_frame(creature, sheet, _animation_state_for(creature, sheet), dt)
        surface.blit(frame, frame.get_rect(center=pos))
        half_height = sheet.frame_height // 2
        ring_radius = sheet.frame_width // 2 - 2
    else:
        _draw_placeholder(surface, creature, pos)
        half_height = RADIUS
        ring_radius = RADIUS + 3

    ring_color = _RARITY_RING.get(creature.rarity)
    if ring_color:
        pygame.draw.circle(surface, ring_color, pos, ring_radius, width=3)

    font = get_font("consolas", 12)
    label = font.render(creature.species.name, True, (255, 255, 255))
    surface.blit(label, (pos[0] - label.get_width() // 2, pos[1] + half_height - 4))


def _draw_placeholder(
    surface: pygame.Surface, creature: Creature, pos: tuple[int, int]
) -> None:
    color = _SPECIES_COLOR.get(creature.species.id, (200, 200, 200))

    if creature.is_clicked_feedback_active():
        pygame.draw.circle(surface, (255, 255, 255), pos, RADIUS + 6, width=2)

    pygame.draw.circle(surface, color, pos, RADIUS)
