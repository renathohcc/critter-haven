"""Loop principal do jogo: janela, eventos, FPS, foco."""

from __future__ import annotations

import pygame

from critter_haven.config.window_states import (
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    state_for_height,
)
from critter_haven.core import window
from critter_haven.data.species import load_planet
from critter_haven.entities.habitat import Habitat
from critter_haven.entities.creature import Creature
from critter_haven.render.creature_render import draw_creature

FPS_FOCUSED = 60
FPS_UNFOCUSED = 15
BACKGROUND_COLOR = (58, 92, 68)
ENERGY_BAR_COLOR = (255, 214, 92)
ENERGY_BAR_BG = (40, 40, 40)


class App:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Critter Haven: Homie's Journey")
        self.surface = pygame.display.set_mode(
            (DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE
        )
        self.clock = pygame.time.Clock()
        self.running = False
        self.focused = True
        self.always_on_top = window.set_always_on_top(True)

        self.habitat = Habitat(
            planet="elyndor",
            species_pool=load_planet("elyndor"),
            max_x=DEFAULT_WIDTH - 20,
        )
        self.selected_creature: Creature | None = None

    def run(self) -> None:
        self.running = True
        while self.running:
            dt = self.clock.tick(FPS_FOCUSED if self.focused else FPS_UNFOCUSED) / 1000.0
            self._handle_events()
            self._update(dt)
            self._render()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.surface = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE
                )
                self.habitat.max_x = event.w - 20
            elif event.type == pygame.WINDOWFOCUSGAINED:
                self.focused = True
            elif event.type == pygame.WINDOWFOCUSLOST:
                self.focused = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

    def _handle_click(self, pos: tuple[int, int]) -> None:
        creature = self.habitat.creature_at(pos[0], pos[1])
        if creature:
            creature.on_click()
            self.selected_creature = creature

    def _update(self, dt: float) -> None:
        self.habitat.update(dt)

    def _render(self) -> None:
        self.surface.fill(BACKGROUND_COLOR)
        self._render_energy_bar()
        for creature in self.habitat.creatures:
            draw_creature(self.surface, creature)
        self._render_selection_panel()
        self._render_debug_overlay()
        pygame.display.flip()

    def _render_energy_bar(self) -> None:
        width, _ = self.surface.get_size()
        bar_width = min(200, width - 24)
        bar_rect = pygame.Rect(12, 12, bar_width, 10)
        pygame.draw.rect(self.surface, ENERGY_BAR_BG, bar_rect)
        fill_rect = bar_rect.copy()
        fill_rect.width = int(bar_rect.width * self.habitat.energy_ratio())
        pygame.draw.rect(self.surface, ENERGY_BAR_COLOR, fill_rect)

    def _render_selection_panel(self) -> None:
        if not self.selected_creature:
            return
        width, height = self.surface.get_size()
        species = self.selected_creature.species
        font = pygame.font.SysFont("consolas", 14)
        lines = [
            f"{species.name} ({species.rarity})",
            f"Produção: {species.base_gold_per_second} ouro/s",
            f"Item: {species.item_name}",
        ]
        panel_height = 20 * len(lines) + 10
        panel = pygame.Rect(10, height - panel_height - 10, min(320, width - 20), panel_height)
        pygame.draw.rect(self.surface, (20, 20, 20), panel)
        pygame.draw.rect(self.surface, (255, 255, 255), panel, width=1)
        for i, line in enumerate(lines):
            surf = font.render(line, True, (255, 255, 255))
            self.surface.blit(surf, (panel.x + 8, panel.y + 8 + i * 20))

    def _render_debug_overlay(self) -> None:
        width, height = self.surface.get_size()
        state = state_for_height(height)
        font = pygame.font.SysFont("consolas", 16)
        lines = [
            "Critter Haven - Fase 2 (habitat e spawn)",
            f"janela: {width}x{height}  estado UI: {state.name}",
            f"criaturas: {len(self.habitat.creatures)}/{self.habitat.max_creatures}"
            f"  FPS: {self.clock.get_fps():.0f}",
        ]
        for i, line in enumerate(lines):
            surf = font.render(line, True, (255, 255, 255))
            self.surface.blit(surf, (12, 30 + i * 20))

    def quit(self) -> None:
        pygame.quit()
