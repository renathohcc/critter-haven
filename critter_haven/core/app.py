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
    OFFLINE_PROGRESS,
    SPAWN_SPEED,
    UPGRADES,
    UPGRADES_BY_ID,
)
from critter_haven.config.window_states import DEFAULT_STATE, next_state, state_by_name
from critter_haven.core import window
from critter_haven.core.menu_bridge import MenuBridge
from critter_haven.data.species import all_species_by_id, load_planet, load_planet_safe
from critter_haven.economy.chest import Chest
from critter_haven.economy.pricing import build_price_map, sell_all
from critter_haven.economy.upgrades import UpgradeManager
from critter_haven.economy.wallet import Wallet
from critter_haven.entities.album import Album
from critter_haven.entities.habitat import Habitat
from critter_haven.entities.creature import Creature
from critter_haven.persistence.save_file import load_game, save_game
from critter_haven.persistence.serializer import build_save_dict, restore_from_save
from critter_haven.render.background import (
    GROUND_BAND_HEIGHT,
    get_background,
    get_foreground_decor,
)
from critter_haven.render.creature_render import creature_top_y, draw_creature
from critter_haven.render.fonts import get_font
from critter_haven.render.tilemap import TileMap, load_map
from critter_haven.render.ui_icons import get_button
from critter_haven.systems.offline_progress import apply_offline_progress
from critter_haven.systems.production_system import update_production
from critter_haven.systems.travel_system import can_travel, travel
from critter_haven.ui.menu_window import run_menu_window

AUTOSAVE_INTERVAL_SECONDS = 30.0
WELCOME_BACK_MIN_ELAPSED_SECONDS = 30.0

FPS_FOCUSED = 30
FPS_UNFOCUSED = 8
FOCUS_CHECK_INTERVAL_SECONDS = 0.5
BACKGROUND_COLOR = (58, 92, 68)
ENERGY_BAR_COLOR = (255, 214, 92)
ENERGY_BAR_BG = (40, 40, 40)
SELL_BUTTON_COLOR = (214, 160, 50)
SELL_BUTTON_HOVER = (240, 185, 70)

ICON_BUTTON_HEIGHT = 30
ICON_BUTTON_GAP = 4
ICON_ROW_Y = 30
# ordem de exibicao (esquerda->direita) da fileira de icones, alinhada a
# direita da janela; cada entrada e (asset, comando_pro_menu ou None)
ICON_ROW_BUTTONS = (
    ("btn_vender_tudo", None),
    ("btn_bau", "habitat"),
    ("btn_upgrades", "habitat"),
    ("btn_nave", "habitat"),
    ("btn_album", "album"),
)
TOP_HUD_HEIGHT = ICON_ROW_Y + ICON_BUTTON_HEIGHT + 4  # limite p/ nao sobrepor criaturas


class App:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Critter Haven: Homie's Journey")

        species_pool = load_planet("elyndor")
        self.habitat = Habitat(planet="elyndor", species_pool=species_pool)
        self._composed_background: dict[tuple[int, int], pygame.Surface] = {}
        self._composed_ground_y: dict[tuple[int, int], int] = {}
        self.wallet = Wallet()
        self.chest = Chest()
        self.price_map = build_price_map(species_pool)
        self.upgrades = UpgradeManager()
        self.album = Album()

        window_state = DEFAULT_STATE
        always_on_top = True
        self.welcome_back_message: str | None = None

        save_dict = load_game()
        if save_dict is not None:
            elapsed = restore_from_save(
                save_dict,
                all_species_by_id(),
                self.wallet,
                self.chest,
                self.habitat,
                self.album,
                self.upgrades,
            )
            window_state = state_by_name(save_dict.get("window_state", DEFAULT_STATE.name))
            always_on_top = save_dict.get("always_on_top", True)
            gold_multiplier = 1.0 + self.upgrades.effect_total(GOLD_PRODUCTION)
            max_offline_seconds = self.upgrades.effect_total(OFFLINE_PROGRESS)
            offline_result = apply_offline_progress(
                self.habitat,
                self.wallet,
                self.chest,
                self.album,
                gold_multiplier,
                elapsed,
                max_offline_seconds,
            )
            self.welcome_back_message = self._build_welcome_back_message(
                offline_result, elapsed, max_offline_seconds
            )

        self.window_state = window_state
        self.surface = pygame.display.set_mode(
            (self.window_state.width, self.window_state.height)
        )
        # pytmx converte imagens (Surface.convert()) ao carregar, o que
        # exige um display já criado -- por isso o mapa só é carregado
        # depois do set_mode acima, não antes.
        self.tile_map: TileMap | None = load_map("elyndor", "Elyndor.tmx")
        self._sync_habitat_bounds()
        self.clock = pygame.time.Clock()
        self.running = False
        self.focused = True
        self.always_on_top = False
        self._apply_always_on_top(always_on_top)

        self.selected_creature: Creature | None = None
        self.sacrifice_button_rect = pygame.Rect(0, 0, 0, 0)
        self.icon_rects: dict[str, pygame.Rect] = {}
        self.last_sale_feedback: str | None = None
        self.last_sale_feedback_timer = 0.0
        self.last_travel_feedback: str | None = None
        self.last_travel_feedback_timer = 0.0
        self.welcome_back_timer = 8.0 if self.welcome_back_message else 0.0
        self.autosave_timer = AUTOSAVE_INTERVAL_SECONDS

        # Janela de menu (Tkinter) roda em thread própria; toda troca de
        # dados passa pelo MenuBridge para evitar duas GUIs mexendo no
        # mesmo estado ao mesmo tempo.
        self.menu_bridge = MenuBridge()
        self.menu_thread = threading.Thread(
            target=run_menu_window, args=(self.menu_bridge,), daemon=True
        )
        self.menu_thread.start()

    @staticmethod
    def _build_welcome_back_message(
        offline_result: dict, raw_elapsed_seconds: float, max_offline_seconds: float
    ) -> str | None:
        if offline_result["elapsed_seconds"] < WELCOME_BACK_MIN_ELAPSED_SECONDS:
            if raw_elapsed_seconds >= WELCOME_BACK_MIN_ELAPSED_SECONDS and max_offline_seconds == 0:
                return (
                    "Homie esperou parado enquanto você esteve fora... "
                    "compre o upgrade de Progresso Offline pra mudar isso!"
                )
            return None
        minutes = int(offline_result["elapsed_seconds"] // 60)
        gold = int(offline_result["gold_gain"])
        parts = [f"Enquanto você esteve fora ({minutes} min), Homie juntou {gold} ouro"]
        if offline_result["spawned_names"]:
            parts.append(f"e encontrou: {', '.join(offline_result['spawned_names'])}")
        return " ".join(parts) + "!"

    def run(self) -> None:
        self.running = True
        while self.running:
            dt = self.clock.tick(FPS_FOCUSED if self.focused else FPS_UNFOCUSED) / 1000.0
            self._refresh_focus_state()
            self._handle_events()
            self._process_menu_commands()
            self._update(dt)
            self._publish_menu_snapshot()
            self._render(dt)

    def _refresh_focus_state(self) -> None:
        # window.is_foreground() (checagem direta via win32) é mais confiável
        # que os eventos WINDOWFOCUSGAINED/LOST do SDL, que ficam inconsistentes
        # com always-on-top ativo — chegavam a reportar foco com outra janela
        # em primeiro plano, prendendo o jogo em 60 FPS o tempo todo.
        foreground = window.is_foreground()
        if foreground is not None:
            self.focused = foreground

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.WINDOWFOCUSGAINED:
                if window.is_foreground() is None:
                    self.focused = True
            elif event.type == pygame.WINDOWFOCUSLOST:
                if window.is_foreground() is None:
                    self.focused = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

    def _handle_click(self, pos: tuple[int, int]) -> None:
        for name, rect in self.icon_rects.items():
            if rect.collidepoint(pos):
                self._handle_icon_click(name)
                return
        if self.sacrifice_button_rect.collidepoint(pos) and self.selected_creature:
            self._sacrifice_duplicate(self.selected_creature.species.id)
            return

        creature = self.habitat.creature_at(pos[0], pos[1])
        if creature:
            creature.on_click()
            self.selected_creature = creature
        else:
            self.selected_creature = None

    def _handle_icon_click(self, name: str) -> None:
        if name == "btn_vender_tudo":
            self._sell_all()
            return
        tab = dict(ICON_ROW_BUTTONS).get(name)
        if tab is not None:
            self.menu_bridge.set_visible(True)
            self.menu_bridge.push_to_menu("select_tab", tab)

    def _sacrifice_duplicate(self, species_id: str) -> None:
        spawned = self.habitat.sacrifice_duplicate_and_spawn(species_id)
        if spawned is None:
            return
        self.album.register(spawned)
        self.selected_creature = None
        self.last_sale_feedback = f"Nova criatura sorteada: {spawned.name}!"
        self.last_sale_feedback_timer = 2.5

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

        album_info = {}
        for planet in PLANETS:
            species_pool = load_planet_safe(planet.id)
            discovered, total = self.album.progress(species_pool)
            entries = []
            for species in species_pool:
                if self.album.is_discovered(species):
                    entries.append(
                        {
                            "id": species.id,
                            "discovered": True,
                            "name": species.name,
                            "rarity": species.rarity,
                            "gold_per_second": species.base_gold_per_second,
                            "item_name": species.item_name,
                            "description": species.description,
                        }
                    )
                else:
                    entries.append({"id": species.id, "discovered": False})
            album_info[planet.id] = {
                "discovered": discovered,
                "total": total,
                "species": entries,
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
                "album": album_info,
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
        self._sync_habitat_bounds()

    def _sync_habitat_bounds(self) -> None:
        self.habitat.max_x = self.window_state.width - 20
        width, height = self.window_state.width, self.window_state.height

        if self.tile_map is not None:
            key = (width, height)
            if key not in self._composed_background:
                surface, ground_y = self.tile_map.compose_for_window(width, height)
                self._composed_background[key] = surface
                self._composed_ground_y[key] = ground_y
            self.habitat.spawn_y = self._composed_ground_y[key]
        else:
            # criaturas devem ficar de pe na faixa de chao do background,
            # nao numa altura fixa arbitraria (bug exposto ao adicionar o
            # chao texturizado com profundidade)
            self.habitat.spawn_y = height - GROUND_BAND_HEIGHT

        for creature in self.habitat.creatures:
            creature.y = self.habitat.spawn_y
        self.habitat.resync_roam_bounds()

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
        spawned = self.habitat.update(dt)
        if spawned:
            self.album.register(spawned)
        gold_multiplier = 1.0 + self.upgrades.effect_total(GOLD_PRODUCTION)
        update_production(
            self.habitat.creatures, dt, self.wallet, self.chest, gold_multiplier
        )
        if self.last_sale_feedback_timer > 0:
            self.last_sale_feedback_timer = max(0.0, self.last_sale_feedback_timer - dt)
        if self.last_travel_feedback_timer > 0:
            self.last_travel_feedback_timer = max(0.0, self.last_travel_feedback_timer - dt)
        if self.welcome_back_timer > 0:
            self.welcome_back_timer = max(0.0, self.welcome_back_timer - dt)

        self.autosave_timer -= dt
        if self.autosave_timer <= 0:
            self._save_game()
            self.autosave_timer = AUTOSAVE_INTERVAL_SECONDS

    def _save_game(self) -> None:
        save_dict = build_save_dict(
            self.wallet,
            self.chest,
            self.habitat,
            self.album,
            self.upgrades,
            self.window_state.name,
            self.always_on_top,
        )
        save_game(save_dict)

    def _render(self, dt: float = 0.0) -> None:
        width, height = self.surface.get_size()
        if self.tile_map is not None:
            self.surface.blit(self._composed_background[(width, height)], (0, 0))
        else:
            background = get_background(self.habitat.planet, width, height)
            if background is not None:
                self.surface.blit(background, (0, 0))
            else:
                self.surface.fill(BACKGROUND_COLOR)
        self._render_energy_bar()
        for creature in self.habitat.creatures:
            draw_creature(self.surface, creature, dt)
        if self.tile_map is None:
            for decor_surface, decor_pos in get_foreground_decor(
                self.habitat.planet, width, height
            ):
                self.surface.blit(decor_surface, decor_pos)
        self._render_hud()
        self._render_icon_row()
        self._render_selection_panel()
        self._render_welcome_back_banner()
        pygame.display.flip()

    def _render_welcome_back_banner(self) -> None:
        if not self.welcome_back_message or self.welcome_back_timer <= 0:
            return
        width, height = self.surface.get_size()
        font = get_font("consolas", 13)
        surf = font.render(self.welcome_back_message, True, (255, 255, 255))
        banner = pygame.Rect(0, 0, min(surf.get_width() + 24, width - 20), 30)
        banner.center = (width // 2, min(70, height - 20))
        pygame.draw.rect(self.surface, (30, 30, 45), banner, border_radius=6)
        pygame.draw.rect(self.surface, (255, 255, 255), banner, width=1, border_radius=6)
        self.surface.blit(surf, surf.get_rect(center=banner.center))

    def _render_energy_bar(self) -> None:
        width, _ = self.surface.get_size()
        bar_width = min(200, width - 24)
        bar_rect = pygame.Rect(12, 12, bar_width, 10)
        pygame.draw.rect(self.surface, ENERGY_BAR_BG, bar_rect)
        fill_rect = bar_rect.copy()
        fill_rect.width = int(bar_rect.width * self.habitat.energy_ratio())
        pygame.draw.rect(self.surface, ENERGY_BAR_COLOR, fill_rect)

        font = get_font("consolas", 11)
        count_text = f"Criaturas: {len(self.habitat.creatures)}/{self.habitat.max_creatures}"
        count_surf = font.render(count_text, True, (230, 230, 230))
        self.surface.blit(count_surf, (bar_rect.right + 8, bar_rect.y - 1))

    def _render_hud(self) -> None:
        width, _ = self.surface.get_size()
        gold_multiplier = 1.0 + self.upgrades.effect_total(GOLD_PRODUCTION)
        gold_per_second = (
            sum(c.gold_per_second for c in self.habitat.creatures) * gold_multiplier
        )
        # Texto reduzido a só o essencial (ouro) — Baú/Upgrades/Nave/Álbum
        # agora têm ícone próprio que abre o menu com o detalhe completo,
        # então não precisa duplicar essa informação em texto solto aqui
        # (pedido do dev: menos texto, mais ícones).
        font = get_font("consolas", 15)
        text = f"Ouro: {self.wallet.gold:.0f}   (+{gold_per_second:.0f}/s)"
        surf = font.render(text, True, (255, 255, 255))
        self.surface.blit(surf, (width - surf.get_width() - 16, 12))

        if self.last_sale_feedback and self.last_sale_feedback_timer > 0:
            feedback_font = get_font("consolas", 13)
            feedback_surf = feedback_font.render(
                self.last_sale_feedback, True, (255, 230, 140)
            )
            self.surface.blit(
                feedback_surf, (width - feedback_surf.get_width() - 16, ICON_ROW_Y + ICON_BUTTON_HEIGHT + 4)
            )

    def _render_icon_row(self) -> None:
        width, _ = self.surface.get_size()
        mouse_pos = pygame.mouse.get_pos()
        self.icon_rects = {}

        # calcula larguras primeiro pra poder alinhar tudo à direita
        buttons = [(name, get_button(name, ICON_BUTTON_HEIGHT)) for name, _tab in ICON_ROW_BUTTONS]
        total_width = sum(b.get_width() for _n, b in buttons) + ICON_BUTTON_GAP * (len(buttons) - 1)
        x = width - 16 - total_width

        for name, icon in buttons:
            rect = pygame.Rect(x, ICON_ROW_Y, icon.get_width(), icon.get_height())
            self.icon_rects[name] = rect
            # leve "aceso" ao passar o mouse — a arte já é rica, então só
            # um brilho sutil (sem trocar de imagem) basta como feedback.
            if rect.collidepoint(mouse_pos):
                glow = icon.copy()
                glow.fill((30, 30, 30, 0), special_flags=pygame.BLEND_RGBA_ADD)
                self.surface.blit(glow, rect)
            else:
                self.surface.blit(icon, rect)
            x += icon.get_width() + ICON_BUTTON_GAP

    def _render_selection_panel(self) -> None:
        self.sacrifice_button_rect = pygame.Rect(0, 0, 0, 0)
        if not self.selected_creature:
            return
        width, height = self.surface.get_size()
        species = self.selected_creature.species
        has_duplicate = self.habitat.has_duplicate(species.id)
        font = get_font("consolas", 14)
        lines = [
            f"{species.name} ({species.rarity})",
            f"Produção: {species.base_gold_per_second} ouro/s",
            f"Item: {species.item_name} ({self.price_map[species.item_name]:.0f} ouro/un.)",
        ]
        panel_height = 20 * len(lines) + 10 + (30 if has_duplicate else 0)
        panel_width = min(300, width - 20)

        # Painel aparece perto da criatura clicada (acima dela, ou abaixo
        # se não houver espaço) em vez de fixo no canto — senão cobre as
        # próprias criaturas quando clicadas perto da borda esquerda
        # (bug relatado pelo dev: painel tampava as criaturas do Mossnib).
        top_margin = TOP_HUD_HEIGHT
        creature_x = int(self.selected_creature.x)
        sprite_top = creature_top_y(self.selected_creature)
        panel_y = sprite_top - 6 - panel_height
        if panel_y < top_margin:
            panel_y = int(self.selected_creature.y) + 6
        panel_x = min(max(creature_x - panel_width // 2, 10), width - 10 - panel_width)
        panel = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        pygame.draw.rect(self.surface, (20, 20, 20), panel)
        pygame.draw.rect(self.surface, (255, 255, 255), panel, width=1)
        for i, line in enumerate(lines):
            surf = font.render(line, True, (255, 255, 255))
            self.surface.blit(surf, (panel.x + 8, panel.y + 8 + i * 20))

        if has_duplicate:
            self.sacrifice_button_rect = pygame.Rect(
                panel.x + 8, panel.y + 8 + len(lines) * 20, panel.width - 16, 24
            )
            mouse_pos = pygame.mouse.get_pos()
            color = (
                SELL_BUTTON_HOVER
                if self.sacrifice_button_rect.collidepoint(mouse_pos)
                else SELL_BUTTON_COLOR
            )
            pygame.draw.rect(self.surface, color, self.sacrifice_button_rect, border_radius=4)
            btn_font = get_font("consolas", 12, bold=True)
            btn_label = btn_font.render(
                "Usar duplicata p/ sortear nova", True, (30, 20, 0)
            )
            self.surface.blit(
                btn_label, btn_label.get_rect(center=self.sacrifice_button_rect.center)
            )

    def quit(self) -> None:
        self._save_game()
        self.menu_bridge.stop_event.set()
        self.menu_thread.join(timeout=2.0)
        pygame.quit()
