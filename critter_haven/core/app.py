"""Loop principal do jogo: janela, eventos, FPS, foco."""

from __future__ import annotations

import pygame

from critter_haven.config.planets import PLANETS
from critter_haven.config.spawn import BASE_MAX_CREATURES, ENERGY_PER_SECOND
from critter_haven.config.upgrades import (
    CHEST_CAPACITY,
    GOLD_PRODUCTION,
    HABITAT_CAPACITY,
    SPAWN_SPEED,
    UPGRADES,
    UPGRADES_BY_ID,
)
from critter_haven.config.window_states import DEFAULT_STATE, next_state
from critter_haven.core import window
from critter_haven.data.species import load_planet
from critter_haven.config.economy import BASE_CHEST_CAPACITY
from critter_haven.economy.chest import Chest
from critter_haven.economy.pricing import build_price_map, sell_all
from critter_haven.economy.upgrades import UpgradeManager
from critter_haven.economy.wallet import Wallet
from critter_haven.entities.habitat import Habitat
from critter_haven.entities.creature import Creature
from critter_haven.render.creature_render import draw_creature
from critter_haven.systems.production_system import update_production
from critter_haven.systems.travel_system import can_travel, travel

FPS_FOCUSED = 60
FPS_UNFOCUSED = 15
BACKGROUND_COLOR = (58, 92, 68)
ENERGY_BAR_COLOR = (255, 214, 92)
ENERGY_BAR_BG = (40, 40, 40)
SELL_BUTTON_COLOR = (214, 160, 50)
SELL_BUTTON_HOVER = (240, 185, 70)
TOOLBAR_BUTTON_COLOR = (70, 70, 70)
TOOLBAR_BUTTON_HOVER = (95, 95, 95)
TOOLBAR_BUTTON_ON_COLOR = (90, 140, 100)


class App:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Critter Haven: Homie's Journey")
        self.window_state = DEFAULT_STATE
        self.surface = pygame.display.set_mode(
            (self.window_state.width, self.window_state.height)
        )
        self.clock = pygame.time.Clock()
        self.running = False
        self.focused = True
        self.always_on_top = False
        self._apply_always_on_top(True)

        species_pool = load_planet("elyndor")
        self.habitat = Habitat(
            planet="elyndor",
            species_pool=species_pool,
            max_x=self.window_state.width - 20,
        )
        self.wallet = Wallet()
        self.chest = Chest()
        self.price_map = build_price_map(species_pool)
        self.upgrades = UpgradeManager()

        self.selected_creature: Creature | None = None
        self.sell_button_rect = pygame.Rect(0, 0, 0, 0)
        self.size_button_rect = pygame.Rect(0, 0, 0, 0)
        self.pin_button_rect = pygame.Rect(0, 0, 0, 0)
        self.ship_nav_rect = pygame.Rect(0, 0, 0, 0)
        self.upgrades_nav_rect = pygame.Rect(0, 0, 0, 0)
        self.ship_open = False
        self.upgrades_open = False
        self.upgrade_buy_rects: dict[str, pygame.Rect] = {}
        self.travel_button_rects: dict[str, pygame.Rect] = {}
        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self.last_sale_feedback: str | None = None
        self.last_sale_feedback_timer = 0.0
        self.last_travel_feedback: str | None = None
        self.last_travel_feedback_timer = 0.0

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
            elif event.type == pygame.WINDOWFOCUSGAINED:
                self.focused = True
            elif event.type == pygame.WINDOWFOCUSLOST:
                self.focused = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

    def _handle_click(self, pos: tuple[int, int]) -> None:
        if self.size_button_rect.collidepoint(pos):
            self._cycle_window_size()
            return
        if self.pin_button_rect.collidepoint(pos):
            self._apply_always_on_top(not self.always_on_top)
            return
        if self.ship_nav_rect.collidepoint(pos):
            self.ship_open = not self.ship_open
            self.upgrades_open = False
            return
        if self.upgrades_nav_rect.collidepoint(pos):
            self.upgrades_open = not self.upgrades_open
            self.ship_open = False
            return

        if self.upgrades_open:
            self._handle_upgrades_click(pos)
            return
        if self.ship_open:
            self._handle_ship_click(pos)
            return

        if self.sell_button_rect.collidepoint(pos):
            self._sell_all()
            return

        creature = self.habitat.creature_at(pos[0], pos[1])
        if creature:
            creature.on_click()
            self.selected_creature = creature
        else:
            self.selected_creature = None

    def _handle_upgrades_click(self, pos: tuple[int, int]) -> None:
        for upgrade_id, rect in self.upgrade_buy_rects.items():
            if rect.collidepoint(pos):
                self.upgrades.buy(UPGRADES_BY_ID[upgrade_id], self.wallet)
                self._apply_upgrade_effects()
                return
        if not self.panel_rect.collidepoint(pos):
            self.upgrades_open = False

    def _handle_ship_click(self, pos: tuple[int, int]) -> None:
        for planet_id, rect in self.travel_button_rects.items():
            if rect.collidepoint(pos):
                destination = next(p for p in PLANETS if p.id == planet_id)
                self._attempt_travel(destination)
                return
        if not self.panel_rect.collidepoint(pos):
            self.ship_open = False

    def _attempt_travel(self, destination) -> None:
        if destination.active:
            return
        if travel(destination, self.chest):
            self.last_travel_feedback = f"Homie viajou para {destination.name}!"
        elif destination.requirement_pending:
            self.last_travel_feedback = "Requisito de viagem ainda não definido."
        else:
            self.last_travel_feedback = (
                f"Faltam itens: {destination.required_item} "
                f"x{destination.required_quantity}"
            )
        self.last_travel_feedback_timer = 3.0

    def _apply_upgrade_effects(self) -> None:
        self.habitat.energy_per_second = ENERGY_PER_SECOND + self.upgrades.effect_total(
            SPAWN_SPEED
        )
        self.habitat.max_creatures = int(
            BASE_MAX_CREATURES + self.upgrades.effect_total(HABITAT_CAPACITY)
        )
        self.chest.capacity = int(
            BASE_CHEST_CAPACITY + self.upgrades.effect_total(CHEST_CAPACITY)
        )

    def _cycle_window_size(self) -> None:
        self.window_state = next_state(self.window_state)
        self.surface = pygame.display.set_mode(
            (self.window_state.width, self.window_state.height)
        )
        self.habitat.max_x = self.window_state.width - 20

    def _apply_always_on_top(self, enabled: bool) -> None:
        window.set_always_on_top(enabled)
        self.always_on_top = enabled

    def _sell_all(self) -> None:
        if self.chest.total_count() == 0:
            self.last_sale_feedback = "Baú vazio."
            self.last_sale_feedback_timer = 2.0
            return
        total = sell_all(self.chest, self.wallet, self.price_map)
        self.last_sale_feedback = f"+{total:.0f} ouro pela venda!"
        self.last_sale_feedback_timer = 2.0

    def _update(self, dt: float) -> None:
        self.habitat.update(dt)
        gold_multiplier = 1.0 + self.upgrades.effect_total(GOLD_PRODUCTION)
        update_production(
            self.habitat.creatures, dt, self.wallet, self.chest, gold_multiplier
        )
        if self.last_sale_feedback_timer > 0:
            self.last_sale_feedback_timer = max(0.0, self.last_sale_feedback_timer - dt)
        if self.last_travel_feedback_timer > 0:
            self.last_travel_feedback_timer = max(0.0, self.last_travel_feedback_timer - dt)

    def _render(self) -> None:
        self.surface.fill(BACKGROUND_COLOR)
        self._render_energy_bar()
        for creature in self.habitat.creatures:
            draw_creature(self.surface, creature)
        self._render_hud()
        self._render_toolbar()
        self._render_sell_button()
        self._render_selection_panel()
        if self.upgrades_open:
            self._render_upgrades_panel()
        elif self.ship_open:
            self._render_ship_panel()
        pygame.display.flip()

    def _render_energy_bar(self) -> None:
        width, _ = self.surface.get_size()
        bar_width = min(200, width - 24)
        bar_rect = pygame.Rect(12, 12, bar_width, 10)
        pygame.draw.rect(self.surface, ENERGY_BAR_BG, bar_rect)
        fill_rect = bar_rect.copy()
        fill_rect.width = int(bar_rect.width * self.habitat.energy_ratio())
        pygame.draw.rect(self.surface, ENERGY_BAR_COLOR, fill_rect)

    def _render_hud(self) -> None:
        width, _ = self.surface.get_size()
        gold_multiplier = 1.0 + self.upgrades.effect_total(GOLD_PRODUCTION)
        gold_per_second = (
            sum(c.gold_per_second for c in self.habitat.creatures) * gold_multiplier
        )
        font = pygame.font.SysFont("consolas", 16)
        text = f"Ouro: {self.wallet.gold:.0f}   (+{gold_per_second:.0f}/s)"
        surf = font.render(text, True, (255, 255, 255))
        self.surface.blit(surf, (width - surf.get_width() - 16, 12))

        chest_font = pygame.font.SysFont("consolas", 13)
        chest_text = f"Baú: {self.chest.total_count()}/{self.chest.capacity} itens"
        chest_surf = chest_font.render(chest_text, True, (230, 230, 230))
        self.surface.blit(chest_surf, (width - chest_surf.get_width() - 16, 32))

        if self.last_sale_feedback and self.last_sale_feedback_timer > 0:
            feedback_surf = chest_font.render(
                self.last_sale_feedback, True, (255, 230, 140)
            )
            self.surface.blit(
                feedback_surf, (width - feedback_surf.get_width() - 16, 50)
            )

    def _render_toolbar(self) -> None:
        font = pygame.font.SysFont("consolas", 12, bold=True)
        mouse_pos = pygame.mouse.get_pos()

        self.size_button_rect = pygame.Rect(12, 28, 90, 22)
        self._draw_toolbar_button(
            self.size_button_rect,
            f"Tamanho: {self.window_state.name}",
            font,
            mouse_pos,
            active=False,
        )

        self.pin_button_rect = pygame.Rect(110, 28, 90, 22)
        self._draw_toolbar_button(
            self.pin_button_rect,
            f"Fixar: {'ON' if self.always_on_top else 'OFF'}",
            font,
            mouse_pos,
            active=self.always_on_top,
        )

        self.ship_nav_rect = pygame.Rect(208, 28, 70, 22)
        self._draw_toolbar_button(
            self.ship_nav_rect, "Nave", font, mouse_pos, active=self.ship_open
        )

        self.upgrades_nav_rect = pygame.Rect(286, 28, 90, 22)
        self._draw_toolbar_button(
            self.upgrades_nav_rect,
            "Upgrades",
            font,
            mouse_pos,
            active=self.upgrades_open,
        )

    def _draw_toolbar_button(
        self,
        rect: pygame.Rect,
        label: str,
        font: pygame.font.Font,
        mouse_pos: tuple[int, int],
        active: bool,
    ) -> None:
        if active:
            color = TOOLBAR_BUTTON_ON_COLOR
        elif rect.collidepoint(mouse_pos):
            color = TOOLBAR_BUTTON_HOVER
        else:
            color = TOOLBAR_BUTTON_COLOR
        pygame.draw.rect(self.surface, color, rect, border_radius=4)
        text = font.render(label, True, (255, 255, 255))
        text_rect = text.get_rect(center=rect.center)
        self.surface.blit(text, text_rect)

    def _render_sell_button(self) -> None:
        width, height = self.surface.get_size()
        button_width, button_height = 130, 34
        self.sell_button_rect = pygame.Rect(
            width - button_width - 16, height - button_height - 12,
            button_width, button_height,
        )
        mouse_pos = pygame.mouse.get_pos()
        color = (
            SELL_BUTTON_HOVER
            if self.sell_button_rect.collidepoint(mouse_pos)
            else SELL_BUTTON_COLOR
        )
        pygame.draw.rect(self.surface, color, self.sell_button_rect, border_radius=6)
        font = pygame.font.SysFont("consolas", 15, bold=True)
        label = font.render("Vender Tudo", True, (30, 20, 0))
        label_pos = (
            self.sell_button_rect.centerx - label.get_width() // 2,
            self.sell_button_rect.centery - label.get_height() // 2,
        )
        self.surface.blit(label, label_pos)

    def _render_selection_panel(self) -> None:
        if not self.selected_creature:
            return
        width, height = self.surface.get_size()
        species = self.selected_creature.species
        font = pygame.font.SysFont("consolas", 14)
        lines = [
            f"{species.name} ({species.rarity})",
            f"Produção: {species.base_gold_per_second} ouro/s",
            f"Item: {species.item_name} ({self.price_map[species.item_name]:.0f} ouro/un.)",
        ]
        panel_height = 20 * len(lines) + 10
        panel = pygame.Rect(10, height - panel_height - 10, min(340, width - 20), panel_height)
        pygame.draw.rect(self.surface, (20, 20, 20), panel)
        pygame.draw.rect(self.surface, (255, 255, 255), panel, width=1)
        for i, line in enumerate(lines):
            surf = font.render(line, True, (255, 255, 255))
            self.surface.blit(surf, (panel.x + 8, panel.y + 8 + i * 20))

    def _render_panel_background(self, title: str) -> pygame.Rect:
        width, height = self.surface.get_size()
        self.panel_rect = pygame.Rect(10, 55, width - 20, height - 65)
        pygame.draw.rect(self.surface, (15, 15, 20), self.panel_rect)
        pygame.draw.rect(self.surface, (255, 255, 255), self.panel_rect, width=1)
        font = pygame.font.SysFont("consolas", 15, bold=True)
        title_surf = font.render(title, True, (255, 255, 255))
        self.surface.blit(title_surf, (self.panel_rect.x + 10, self.panel_rect.y + 8))
        return self.panel_rect

    def _render_upgrades_panel(self) -> None:
        panel = self._render_panel_background("Upgrades")
        self.upgrade_buy_rects.clear()
        font = pygame.font.SysFont("consolas", 13)
        row_y = panel.y + 32
        row_height = min(30, max(18, (panel.height - 40) // len(UPGRADES)))

        for upgrade in UPGRADES:
            level = self.upgrades.level(upgrade.id)
            cost = self.upgrades.cost(upgrade)
            label = f"{upgrade.name} (nv {level}/{upgrade.max_level})"
            label_surf = font.render(label, True, (230, 230, 230))
            self.surface.blit(label_surf, (panel.x + 10, row_y + 4))

            buy_rect = pygame.Rect(panel.right - 130, row_y, 120, row_height - 4)
            can_afford = cost is not None and self.wallet.can_afford(cost)
            if cost is None:
                color, text = (80, 80, 80), "MAX"
            elif can_afford:
                color, text = SELL_BUTTON_COLOR, f"{cost:.0f} ouro"
            else:
                color, text = (90, 60, 60), f"{cost:.0f} ouro"
            pygame.draw.rect(self.surface, color, buy_rect, border_radius=4)
            btn_surf = font.render(text, True, (20, 20, 20) if cost else (200, 200, 200))
            self.surface.blit(btn_surf, btn_surf.get_rect(center=buy_rect.center))
            self.upgrade_buy_rects[upgrade.id] = buy_rect

            row_y += row_height

    def _render_ship_panel(self) -> None:
        panel = self._render_panel_background("Nave — Destinos")
        self.travel_button_rects.clear()
        font = pygame.font.SysFont("consolas", 13)
        row_y = panel.y + 32
        row_height = min(34, max(20, (panel.height - 40) // len(PLANETS)))

        for planet in PLANETS:
            if planet.active:
                status = "Atual"
            elif planet.requirement_pending:
                status = "Bloqueado (requisito a definir)"
            elif can_travel(planet, self.chest):
                status = "Requisito atendido!"
            else:
                have = self.chest.items.get(planet.required_item, 0)
                status = f"Precisa: {planet.required_item} ({have}/{planet.required_quantity})"

            label = f"{planet.name} — {planet.theme}"
            label_surf = font.render(label, True, (230, 230, 230))
            self.surface.blit(label_surf, (panel.x + 10, row_y))
            status_surf = font.render(status, True, (200, 200, 140))
            self.surface.blit(status_surf, (panel.x + 10, row_y + 16))

            if not planet.active:
                travel_rect = pygame.Rect(panel.right - 100, row_y + 4, 90, row_height - 8)
                enabled = can_travel(planet, self.chest)
                color = SELL_BUTTON_COLOR if enabled else (70, 70, 70)
                pygame.draw.rect(self.surface, color, travel_rect, border_radius=4)
                btn_surf = font.render("Viajar", True, (20, 20, 20))
                self.surface.blit(btn_surf, btn_surf.get_rect(center=travel_rect.center))
                self.travel_button_rects[planet.id] = travel_rect

            row_y += row_height

        if self.last_travel_feedback and self.last_travel_feedback_timer > 0:
            feedback_surf = font.render(self.last_travel_feedback, True, (255, 230, 140))
            self.surface.blit(feedback_surf, (panel.x + 10, panel.bottom - 22))

    def quit(self) -> None:
        pygame.quit()
