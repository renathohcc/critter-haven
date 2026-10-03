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
from critter_haven.core import audio, window
from critter_haven.core.menu_bridge import MenuBridge
from critter_haven.data.species import all_species_by_id, load_planet, load_planet_safe
from critter_haven.economy.chest import Chest
from critter_haven.economy.pricing import build_price_map, sell_all, sell_item
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
from critter_haven.render.energy_bar import draw_energy_bar
from critter_haven.render.stat_badge import draw_stat_badge
from critter_haven.render.creature_render import (
    creature_half_width,
    creature_top_y,
    draw_creature,
)
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

ICON_BUTTON_HEIGHT = 48
ICON_BUTTON_GAP = 6
ICON_ROW_Y = 6
# ordem de exibicao (esquerda->direita) da fileira de icones, alinhada a
# direita da janela; cada entrada e (asset, nome_da_janela_de_menu ou None).
# Cada janela e independente (nao existe mais um notebook unico) -- ver
# critter_haven/ui/menu_window.py.
ICON_ROW_BUTTONS = (
    ("btn_vender_tudo", None),
    ("btn_bau", "bau"),
    ("btn_upgrades", "upgrades"),
    ("btn_nave", "nave"),
    ("btn_fusao", "fusion"),
    ("btn_album", "album"),
    ("btn_config", "config"),
)
TOP_HUD_HEIGHT = ICON_ROW_Y + ICON_BUTTON_HEIGHT + 6 + 95  # icones + selos de ouro/bau/venda


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
            saved_audio = save_dict.get("audio", {})
            audio.set_music_volume(saved_audio.get("music", audio.DEFAULT_USER_VOLUME))
            audio.set_sfx_volume(saved_audio.get("sfx", audio.DEFAULT_USER_VOLUME))
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

        audio.start_habitat_music()
        if self.welcome_back_message:
            audio.play_sfx("welcome_back")

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
        self.icon_rects: dict[str, pygame.Rect] = {}
        self.last_sale_feedback: str | None = None
        self.last_sale_feedback_timer = 0.0
        self.last_travel_feedback: str | None = None
        self.last_travel_feedback_timer = 0.0
        self.last_fusion_result: str | None = None
        self._album_complete_announced = self._album_is_complete()
        self._energy_full_announced = False
        self.animation_time = 0.0
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

        creature = self.habitat.creature_at(pos[0], pos[1])
        if creature:
            audio.play_sfx("click_creature")
            creature.on_click()
            self.selected_creature = creature
        else:
            self.selected_creature = None

    def _handle_icon_click(self, name: str) -> None:
        if name == "btn_vender_tudo":
            self._sell_all()
            return
        audio.play_sfx("ui_click")
        window_name = dict(ICON_ROW_BUTTONS).get(name)
        if window_name is not None:
            self.menu_bridge.push_to_menu("show_window", window_name)

    def _process_menu_commands(self) -> None:
        for name, payload in self.menu_bridge.drain_commands():
            if name == "cycle_size":
                self._cycle_window_size()
            elif name == "toggle_pin":
                self._apply_always_on_top(not self.always_on_top)
            elif name == "buy_upgrade":
                if self.upgrades.buy(UPGRADES_BY_ID[payload], self.wallet):
                    audio.play_sfx("buy_upgrade")
                self._apply_upgrade_effects()
            elif name == "travel":
                destination = next(p for p in PLANETS if p.id == payload)
                self._attempt_travel(destination)
            elif name == "sell_all":
                self._sell_all()
            elif name == "sell_item":
                item_name, quantity = payload
                if sell_item(self.chest, self.wallet, self.price_map, item_name, quantity) > 0:
                    audio.play_sfx("sell")
            elif name == "fuse":
                self._fuse_creatures(*payload)
            elif name == "sfx":
                audio.play_sfx(payload)
            elif name == "set_music_volume":
                audio.set_music_volume(payload)
            elif name == "set_sfx_volume":
                audio.set_sfx_volume(payload)

    def _album_is_complete(self) -> bool:
        discovered, total = self.album.progress(self.habitat.species_pool)
        return total > 0 and discovered == total

    def _check_album_complete(self) -> None:
        if not self._album_complete_announced and self._album_is_complete():
            self._album_complete_announced = True
            audio.play_sfx("album_complete")

    def _fuse_creatures(self, creature_id_a: int, creature_id_b: int) -> None:
        spawned = self.habitat.fuse_creatures(creature_id_a, creature_id_b)
        if spawned is None:
            self.last_fusion_result = "Fusão falhou: escolha 2 criaturas diferentes."
            return
        self.album.register(spawned)
        audio.play_sfx("fuse")
        self._check_album_complete()
        if self.selected_creature is not None and id(self.selected_creature) in (
            creature_id_a,
            creature_id_b,
        ):
            self.selected_creature = None
        self.last_fusion_result = f"Fusão gerou: {spawned.name} ({spawned.rarity})!"

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

        creatures_info = [
            {"id": id(c), "species_id": c.species.id, "name": c.species.name, "rarity": c.rarity}
            for c in self.habitat.creatures
        ]

        # detalhamento por item (Fase 8.6: Baú vende item a item, nao so
        # tudo de uma vez) -- sempre lista todas as especies do habitat,
        # mesmo com 0 no baú, pra o jogador ver todas as categorias.
        chest_items_info = [
            {
                "item_name": species.item_name,
                "species_id": species.id,
                "species_name": species.name,
                "rarity": species.rarity,
                "count": self.chest.items.get(species.item_name, 0),
                "price": self.price_map.get(species.item_name, 0.0),
            }
            for species in self.habitat.species_pool
        ]

        self.menu_bridge.publish(
            {
                "gold": self.wallet.gold,
                "gold_per_second": gold_per_second,
                "creature_count": len(self.habitat.creatures),
                "max_creatures": self.habitat.max_creatures,
                "chest_count": self.chest.total_count(),
                "chest_capacity": self.chest.capacity,
                "chest_items": chest_items_info,
                "window_state": self.window_state.name,
                "album": album_info,
                "always_on_top": self.always_on_top,
                "music_volume": audio.get_volumes()[0],
                "sfx_volume": audio.get_volumes()[1],
                "upgrades": upgrades_info,
                "planets": planets_info,
                "creatures": creatures_info,
                "last_fusion_result": self.last_fusion_result,
            }
        )

    def _attempt_travel(self, destination) -> None:
        if destination.active:
            return
        if travel(destination, self.chest):
            audio.play_sfx("travel")
            self.last_travel_feedback = f"Homie viajou para {destination.name}!"
        elif destination.requirement_pending:
            audio.play_sfx("denied")
            self.last_travel_feedback = "Requisito de viagem ainda não definido."
        else:
            audio.play_sfx("denied")
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
            audio.play_sfx("denied")
            self.last_sale_feedback = "Baú vazio."
            self.last_sale_feedback_timer = 2.0
            return
        total = sell_all(self.chest, self.wallet, self.price_map)
        audio.play_sfx("sell")
        self.last_sale_feedback = f"+{total:.0f} ouro pela venda!"
        self.last_sale_feedback_timer = 2.0

    def _update(self, dt: float) -> None:
        self.animation_time += dt
        spawned = self.habitat.update(dt)
        if spawned:
            self.album.register(spawned)
            audio.play_sfx("spawn")
            self._check_album_complete()
        # energia cheia so "fica" cheia quando o habitat esta lotado (senao
        # ja nasceu uma criatura): avisa uma vez por enchimento, pro
        # jogador saber que precisa abrir espaco
        if self.habitat.is_full and self.habitat.energy_ratio() >= 0.999:
            if not self._energy_full_announced:
                self._energy_full_announced = True
                audio.play_sfx("energy_full")
        elif self.habitat.energy_ratio() < 0.999:
            self._energy_full_announced = False
        gold_multiplier = 1.0 + self.upgrades.effect_total(GOLD_PRODUCTION)
        items_added = update_production(
            self.habitat.creatures, dt, self.wallet, self.chest, gold_multiplier
        )
        if items_added:
            audio.play_sfx("item_drop")
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
            {"music": audio.get_volumes()[0], "sfx": audio.get_volumes()[1]},
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
        bar_height = 18
        bar_rect = pygame.Rect(12, 12, bar_width, bar_height)
        draw_energy_bar(
            self.surface,
            bar_rect.x,
            bar_rect.y,
            bar_rect.width,
            bar_rect.height,
            self.habitat.energy_ratio(),
            self.animation_time,
        )

        count_text = f"{len(self.habitat.creatures)}/{self.habitat.max_creatures}"
        draw_stat_badge(
            self.surface, bar_rect.right + 8, bar_rect.y - 1, "icon_paw", count_text,
            icon_height=bar_height, font_size=13,
        )

    def _render_hud(self) -> None:
        width, _ = self.surface.get_size()
        gold_multiplier = 1.0 + self.upgrades.effect_total(GOLD_PRODUCTION)
        gold_per_second = (
            sum(c.gold_per_second for c in self.habitat.creatures) * gold_multiplier
        )
        # Selos (ícone + texto numa pilula escura) em vez de texto solto —
        # Baú/Upgrades/Nave/Álbum já têm ícone próprio que abre o menu com
        # o detalhe completo, então aqui só o essencial, compacto e com
        # contraste garantido contra o cenário (pedido do dev: bonito,
        # visível, sem poluir a UI).
        badge_y = ICON_ROW_Y + ICON_BUTTON_HEIGHT + 6

        gold_text = f"{self.wallet.gold:.0f}  (+{gold_per_second:.0f}/s)"
        gold_rect = draw_stat_badge(
            self.surface, width - 16, badge_y, "icon_coin", gold_text,
            icon_height=20, font_size=15, align="right",
        )

        chest_text = f"{self.chest.total_count()}/{self.chest.capacity}"
        chest_rect = draw_stat_badge(
            self.surface, width - 16, gold_rect.bottom + 4, "icon_chest", chest_text,
            icon_height=18, font_size=13, align="right",
        )

        if self.last_sale_feedback and self.last_sale_feedback_timer > 0:
            feedback_font = get_font("consolas", 13)
            feedback_surf = feedback_font.render(
                self.last_sale_feedback, True, (255, 230, 140)
            )
            self.surface.blit(
                feedback_surf,
                (width - feedback_surf.get_width() - 16, chest_rect.bottom + 4),
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
        if not self.selected_creature:
            return
        width, height = self.surface.get_size()
        species = self.selected_creature.species
        font = get_font("consolas", 14)
        lines = [
            f"{species.name} ({species.rarity})",
            f"Produção: {species.base_gold_per_second} ouro/s",
            f"Item: {species.item_name} ({self.price_map[species.item_name]:.0f} ouro/un.)",
        ]
        panel_height = 20 * len(lines) + 10
        panel_width = min(300, width - 20)

        # Painel aparece perto da criatura clicada (acima dela, ou abaixo
        # se não houver espaço) em vez de fixo no canto — senão cobre as
        # próprias criaturas quando clicadas perto da borda esquerda
        # (bug relatado pelo dev: painel tampava as criaturas do Mossnib).
        top_margin = TOP_HUD_HEIGHT
        creature_x = int(self.selected_creature.x)
        sprite_top = creature_top_y(self.selected_creature)
        sprite_bottom = int(self.selected_creature.y)
        panel_y = sprite_top - 6 - panel_height
        fits_above = panel_y >= top_margin
        fits_below = sprite_bottom + 6 + panel_height <= height - 10
        if fits_above:
            panel_x = min(max(creature_x - panel_width // 2, 10), width - 10 - panel_width)
        elif fits_below:
            panel_y = sprite_bottom + 6
            panel_x = min(max(creature_x - panel_width // 2, 10), width - 10 - panel_width)
        else:
            # nem acima nem abaixo cabe (criatura ocupa quase toda a
            # altura) — poe o painel do lado (direita, ou esquerda se nao
            # houver espaco) em vez de por cima da criatura, senao a
            # animacao de clique fica escondida atras do painel.
            half_width = creature_half_width(self.selected_creature)
            panel_y = min(max(sprite_top, top_margin), height - 10 - panel_height)
            space_right = width - 10 - (creature_x + half_width + 8)
            if space_right >= panel_width:
                panel_x = int(creature_x + half_width + 8)
            else:
                panel_x = int(creature_x - half_width - 8 - panel_width)
                panel_x = max(panel_x, 10)
        panel = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        pygame.draw.rect(self.surface, (20, 20, 20), panel)
        pygame.draw.rect(self.surface, (255, 255, 255), panel, width=1)
        for i, line in enumerate(lines):
            surf = font.render(line, True, (255, 255, 255))
            self.surface.blit(surf, (panel.x + 8, panel.y + 8 + i * 20))

    def quit(self) -> None:
        self._save_game()
        self.menu_bridge.stop_event.set()
        self.menu_thread.join(timeout=2.0)
        pygame.quit()
