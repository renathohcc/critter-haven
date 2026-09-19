"""Desenho das criaturas. Usa sprite real (spritesheet + animação) se a
espécie já tiver assets em assets/creatures/; caso contrário cai no
placeholder geométrico — permite trocar espécie por espécie sem quebrar
as demais nem tocar em lógica de jogo.

"Respirar" (leve pulso de escala) e o flash de clique são efeitos
aplicados por código em cima do sprite, não frames de arte — dá vida
ao personagem sem precisar gerar mais quadros na IA para cada espécie.
"""

from __future__ import annotations

import math

import pygame

from critter_haven.entities.creature import Creature
from critter_haven.render.animation import current_frame
from critter_haven.render.fonts import get_font
from critter_haven.render.spritesheet import load_creature_sheet

RADIUS = 20
BREATH_PERIOD_SECONDS = 2.6
BREATH_AMPLITUDE = 0.05

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
    desired = "walk_left" if creature.direction < 0 else "walk_right"
    if sheet.has_state(desired):
        return desired
    if sheet.has_state("walk"):
        return "walk"
    return "idle"


def _breathing_scale(creature: Creature) -> float:
    phase = pygame.time.get_ticks() / 1000.0 / BREATH_PERIOD_SECONDS * (2 * math.pi)
    phase += (id(creature) % 1000) * 0.01  # dessincroniza criaturas iguais
    return 1.0 + BREATH_AMPLITUDE * math.sin(phase)


def draw_creature(surface: pygame.Surface, creature: Creature, dt: float = 0.0) -> None:
    pos = (int(creature.x), int(creature.y))
    sheet = load_creature_sheet(creature.species.id)

    if sheet is not None:
        state = _animation_state_for(creature, sheet)
        frame = current_frame(creature, sheet, state, dt)
        scale = _breathing_scale(creature)
        if scale != 1.0:
            w, h = frame.get_size()
            frame = pygame.transform.smoothscale(
                frame, (max(1, round(w * scale)), max(1, round(h * scale)))
            )
        rect = frame.get_rect(center=pos)
        if creature.is_clicked_feedback_active():
            pygame.draw.circle(surface, (255, 255, 255), pos, RADIUS + 6, width=2)
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
