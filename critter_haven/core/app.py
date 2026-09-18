"""Loop principal do jogo: janela, eventos, FPS, foco."""

from __future__ import annotations

import threading

import pygame

from critter_haven.config.economy import BASE_CHEST_CAPACITY
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
from critter_haven.core.menu_bridge import MenuBridge
from critter_haven.data.species import load_planet
from critter_haven.economy.chest import Chest
from critter_haven.economy.pricing import build_price_map, sell_all
from critter_haven.economy.upgrades import UpgradeManager
from critter_haven.economy.wallet import Wallet
from critter_haven.entities.habitat import Habitat
from critter_haven.entities.creature import Creature
from critter_haven.render.creature_render import draw_creature
from critter_haven.systems.production_system import update_production
from critter_haven.systems.travel_system import can_travel, travel
from critter_haven.ui.menu_window import run_menu_window

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
        self.menu_button_rect = pygame.Rect(0, 0, 0, 0)
        self.last_sale_feedback: str | None = None
        self.last_sale_feedback_timer = 0.0
        self.last_travel_feedback: str | None = None
        self.last_travel_feedback_timer = 0.0

        # Janela de menu (Tkinter) roda em thread própria; toda troca de
        # dados passa pelo MenuBridge para evitar duas GUIs mexendo no
        # mesmo estado ao mesmo tempo.
        self.menu_bridge = MenuBridge()
        self.menu_thread = threading.Thread(
            target=run_menu_window, args=(self.menu_bridge,), daemon=True
        )
        self.menu_thread.start()

    def run(self) -> None:
        self.running = True
        while self.running:
            dt = self.clock.tick(FPS_FOCUSED if self.focused else FPS_UNFOCUSED) / 1000.0
            self._handle_events()
            self._process_menu_commands()
            self._update(dt)
            self._publish_menu_snapshot()
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
        if self.menu_button_rect.collidepoint(pos):
            self.menu_bridge.toggle_visible()
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

    def _process_menu_commands(self) -> None:
        for name, payload in self.menu_bridge.drain_commands():
            if name == "cycle_size":
                self._cycle_window_size()
            elif name == "toggle_pin":
                self._apply_always_on_top(not self.always_on_top)
            elif name == "buy_upgrade":
                self.upgrades.buy(UPGRADES_BY_ID[payload], self.wallet)
                self._apply_upgrade_effects()
            elif name == "travel":
                destination = next(p for p in PLANETS if p.id == payload)
                self._attempt_travel(destination)
            elif name == "sell_all":
                self._sell_all()

    def _publish_menu_snapshot(self) -> None:
        gold_multiplier = 1.0 + self.upgrades.effect_total(GOLD_PRODUCTION)
        gold_per_second = (
            sum(c.gold_per_second for c in self.habitat.creatures) * gold_multiplier
        )
        upgrades_info = {
            u.id: {
                "level": self.upgrades.level(u.id),
                "cost": self.upgrades.cost(u),
                "can_afford": (
                    self.upgrades.cost(u) is not None
                    and self.wallet.can_afford(self.upgrades.cost(u))
                ),
            }
            for u in UPGRADES
        }
        planets_info = {}
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
            planets_info[planet.id] = {
                "status": status,
                "can_travel": can_travel(planet, self.chest),
            }

        self.menu_bridge.publish(
            {
                "gold": self.wallet.gold,
                "gold_per_second": gold_per_second,
                "creature_count": len(self.habitat.creatures),
                "max_creatures": self.habitat.max_creatures,
                "chest_count": self.chest.total_count(),
                "chest_capacity": self.chest.capacity,
                "window_state": self.window_state.name,
                "always_on_top": self.always_on_top,
                "upgrades": upgrades_info,
                "planets": planets_info,
            }
        )

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
        self._render_menu_button()
        self._render_sell_button()
        self._render_selection_panel()
        pygame.display.flip()

    def _render_energy_bar(self) -> None:
        width, _ = self.surface.get_size()
        bar_width = min(200, width - 24)
        bar_rect = pygame.Rect(12, 12, bar_width, 10)
        pygame.draw.rect(self.surface, ENERGY_BAR_BG, bar_rect)
        fill_rect = bar_rect.copy()
        fill_rect.width = int(bar_rect.width * self.habitat.energy_ratio())
        pygame.draw.rect(self.surface, ENERGY_BAR_COLOR, fill_rect)

        font = pygame.font.SysFont("consolas", 11)
        count_text = f"Criaturas: {len(self.habitat.creatures)}/{self.habitat.max_creatures}"
        count_surf = font.render(count_text, True, (230, 230, 230))
        self.surface.blit(count_surf, (bar_rect.right + 8, bar_rect.y - 1))

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

    def _render_menu_button(self) -> None:
        font = pygame.font.SysFont("consolas", 12, bold=True)
        mouse_pos = pygame.mouse.get_pos()
        self.menu_button_rect = pygame.Rect(12, 28, 90, 22)
        active = self.menu_bridge.is_visible()
        color = (
            TOOLBAR_BUTTON_ON_COLOR
            if active
            else TOOLBAR_BUTTON_HOVER
            if self.menu_button_rect.collidepoint(mouse_pos)
            else TOOLBAR_BUTTON_COLOR
        )
        pygame.draw.rect(self.surface, color, self.menu_button_rect, border_radius=4)
        text = font.render("Menu", True, (255, 255, 255))
        self.surface.blit(text, text.get_rect(center=self.menu_button_rect.center))

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

    def quit(self) -> None:
        self.menu_bridge.stop_event.set()
        self.menu_thread.join(timeout=2.0)
        pygame.quit()
