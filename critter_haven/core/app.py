"""Loop principal do jogo: janela, eventos, FPS, foco."""

from __future__ import annotations

import pygame

from critter_haven.config.window_states import (
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    state_for_height,
)
from critter_haven.core import window

FPS_FOCUSED = 60
FPS_UNFOCUSED = 15
BACKGROUND_COLOR = (58, 92, 68)


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
            elif event.type == pygame.WINDOWFOCUSGAINED:
                self.focused = True
            elif event.type == pygame.WINDOWFOCUSLOST:
                self.focused = False

    def _update(self, dt: float) -> None:
        pass

    def _render(self) -> None:
        self.surface.fill(BACKGROUND_COLOR)
        self._render_debug_overlay()
        pygame.display.flip()

    def _render_debug_overlay(self) -> None:
        width, height = self.surface.get_size()
        state = state_for_height(height)
        font = pygame.font.SysFont("consolas", 16)
        lines = [
            f"Critter Haven - Fase 1 (fundacao)",
            f"janela: {width}x{height}  estado UI: {state.name}",
            f"always-on-top ativo: {self.always_on_top}",
            f"FPS: {self.clock.get_fps():.0f}",
        ]
        for i, line in enumerate(lines):
            surf = font.render(line, True, (255, 255, 255))
            self.surface.blit(surf, (12, 12 + i * 20))

    def quit(self) -> None:
        pygame.quit()
