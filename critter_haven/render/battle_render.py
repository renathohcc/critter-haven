"""Desenho da batalha de defesa (Fase 11.4): nave à esquerda, criaturas
na posição do seu papel, inimigos entrando pela direita, barras de vida,
números flutuantes e os botões da batalha. Só lê o estado do `Battle`
(systems/combat_system.py) -- nunca o modifica.

Inimigos ainda são placeholders geométricos (como as criaturas foram no
começo); a arte de verdade entra na 11.7."""

from __future__ import annotations

import pygame

from critter_haven.render.fonts import get_font
from critter_haven.render.spritesheet import load_creature_sheet, load_enemy_sheet
from critter_haven.systems.cards import Card
from critter_haven.systems.combat_system import FIELD_LENGTH, Battle

SHIP_SCREEN_X = 56
FIELD_MARGIN_RIGHT = 70

HP_BG = (30, 20, 20)
HP_UNIT = (110, 200, 110)
HP_ENEMY = (220, 90, 80)
HP_SHIP = (110, 170, 230)
TEXT = (240, 230, 205)
GOLD = (244, 214, 147)

ENEMY_LOOK = {
    "grunt": ((150, 90, 60), (22, 22)),
    "runner": ((200, 170, 70), (16, 16)),
    "brute": ((110, 60, 90), (34, 34)),
    "spitter": ((90, 140, 90), (20, 20)),
    "boss": ((150, 40, 50), (64, 64)),
}

SPEEDS = (1, 2, 4)
ATTACK_ANIM_SECONDS = 0.8
WALK_GRACE_SECONDS = 0.12


class BattleView:
    def __init__(self) -> None:
        self.speed_index = 0
        self.floaters: list[list] = []  # [x, y, texto, cor, ttl]
        self._buttons: dict[str, pygame.Rect] = {}
        self.choices: list[Card] = []  # cartas ofertadas (entre as waves)
        self._flipped_cache: dict[tuple[str, str, int], pygame.Surface] = {}
        # estado de animacao dos inimigos com arte (por uid)
        self._enemy_last: dict[int, tuple[float, str]] = {}  # uid -> (sx, tipo)
        self._enemy_prev_x: dict[int, float] = {}
        self._attack_until: dict[int, float] = {}
        self._moved_at: dict[int, float] = {}
        self._unit_attack_start: dict[int, float] = {}
        self._dying: list[list] = []  # [sx, tipo, inicio]
        self._now = 0.0

    @property
    def speed(self) -> int:
        return SPEEDS[self.speed_index]

    # ------------------------------------------------------------ mapa
    @staticmethod
    def screen_x(x: float, width: int) -> float:
        usable = width - SHIP_SCREEN_X - FIELD_MARGIN_RIGHT
        return SHIP_SCREEN_X + 30 + x * usable / FIELD_LENGTH

    # ---------------------------------------------------------- desenho
    def draw(
        self,
        surface: pygame.Surface,
        battle: Battle,
        anim_time: float,
        ground_y: float,
        mouse_pos: tuple[int, int],
        events: list | None = None,
    ) -> None:
        width, height = surface.get_size()
        positions: dict[int, tuple[float, float]] = {}
        events = battle.events if events is None else events
        self._now = anim_time
        self._consume_enemy_events(events, {u.uid for u in battle.units}, anim_time)

        self._draw_ship(surface, battle, ground_y)
        for unit in battle.units:
            sx = self.screen_x(unit.x, width)
            positions[unit.uid] = (sx, ground_y - 24)
            self._draw_unit(surface, unit, sx, ground_y, anim_time)
        for enemy in battle.enemies:
            sx = self.screen_x(enemy.x, width)
            colour, size = ENEMY_LOOK.get(enemy.stats.enemy_id, ((150, 150, 150), (20, 20)))
            positions[enemy.uid] = (sx, ground_y - size[1])
            self._draw_enemy(surface, enemy, sx, ground_y, colour, size)
        positions[0] = (SHIP_SCREEN_X, ground_y - 40)
        self._draw_dying(surface, ground_y, anim_time)

        self._collect_floaters(events, positions)
        self._draw_floaters(surface)
        self._draw_hud(surface, battle, mouse_pos)

    def _bar(self, surface, centre_x, y, width, ratio, colour) -> None:
        rect = pygame.Rect(0, 0, width, 5)
        rect.midbottom = (int(centre_x), int(y))
        pygame.draw.rect(surface, HP_BG, rect)
        fill = rect.copy()
        fill.width = max(0, int(rect.width * max(0.0, min(1.0, ratio))))
        pygame.draw.rect(surface, colour, fill)

    def _draw_ship(self, surface, battle: Battle, ground_y: float) -> None:
        body = pygame.Rect(0, 0, 54, 46)
        body.midbottom = (SHIP_SCREEN_X, int(ground_y))
        pygame.draw.rect(surface, (70, 74, 92), body, border_radius=8)
        pygame.draw.rect(surface, (9, 2, 2), body, width=3, border_radius=8)
        pygame.draw.circle(surface, (150, 190, 230), (body.centerx, body.y + 16), 8)
        pygame.draw.polygon(
            surface, (200, 80, 70),
            [(body.centerx, body.y - 16), (body.centerx - 8, body.y), (body.centerx + 8, body.y)],
        )
        self._bar(surface, SHIP_SCREEN_X, body.y - 18, 60, battle.ship.hp / battle.ship.max_hp, HP_SHIP)

    def _draw_unit(self, surface, unit, sx: float, ground_y: float, anim_time: float) -> None:
        sheet = load_creature_sheet(unit.stats.species_id)
        alpha = 255 if unit.alive else 90
        if sheet is not None:
            state, elapsed = "idle", anim_time
            started = self._unit_attack_start.get(unit.uid)
            if started is not None and sheet.has_state("attack"):
                length = len(sheet.state_frames("attack")) / sheet.state_fps("attack")
                if anim_time - started < length:
                    state, elapsed = "attack", anim_time - started
            frames = sheet.state_frames(state)
            fps = sheet.state_fps(state)
            index = int(elapsed * fps)
            index = index % len(frames) if state == "idle" else min(index, len(frames) - 1)
            # os sprites olham pra esquerda; na batalha as criaturas encaram
            # a direita, de onde vem os inimigos
            key = (unit.stats.species_id, state, index)
            if key not in self._flipped_cache:
                self._flipped_cache[key] = pygame.transform.flip(frames[index], True, False)
            image = self._flipped_cache[key].copy()
            image.set_alpha(alpha)
            rect = image.get_rect(midbottom=(int(sx), int(ground_y + sheet.ground_offset)))
            surface.blit(image, rect)
            top = rect.top + 4
        else:
            pygame.draw.circle(surface, (120, 200, 120), (int(sx), int(ground_y) - 14), 14)
            top = ground_y - 30
        if unit.alive:
            self._bar(surface, sx, top, 30, unit.hp / unit.max_hp, HP_UNIT)

    def _consume_enemy_events(self, events, unit_ids: set[int], now: float) -> None:
        for event in events:
            if event.kind == "hit" and event.source in unit_ids:
                self._unit_attack_start[event.source] = now
            elif event.kind == "hit" and event.source != 0:
                self._attack_until[event.source] = now + ATTACK_ANIM_SECONDS
            elif event.kind == "death" and event.target in self._enemy_last:
                sx, kind = self._enemy_last.pop(event.target)
                self._enemy_prev_x.pop(event.target, None)
                self._attack_until.pop(event.target, None)
                if load_enemy_sheet(kind) is not None:
                    self._dying.append([sx, kind, now])

    def _draw_sheet_frame(self, surface, sheet, state: str, elapsed: float, sx, ground_y, loop=True):
        frames = sheet.state_frames(state)
        index = int(elapsed * sheet.state_fps(state))
        index = index % len(frames) if loop else min(index, len(frames) - 1)
        rect = frames[index].get_rect(midbottom=(int(sx), int(ground_y + sheet.ground_offset)))
        surface.blit(frames[index], rect)
        return rect

    def _draw_dying(self, surface, ground_y: float, now: float) -> None:
        remaining = []
        for entry in self._dying:
            sx, kind, start = entry
            sheet = load_enemy_sheet(kind)
            length = len(sheet.state_frames("death")) / sheet.state_fps("death")
            if now - start <= length + 0.4:
                self._draw_sheet_frame(surface, sheet, "death", now - start, sx, ground_y, loop=False)
                remaining.append(entry)
        self._dying = remaining

    def _draw_enemy(self, surface, enemy, sx: float, ground_y: float, colour, size) -> None:
        sheet = load_enemy_sheet(enemy.stats.enemy_id)
        if sheet is not None:
            self._draw_enemy_sprite(surface, enemy, sheet, sx, ground_y)
            return
        rect = pygame.Rect(0, 0, *size)
        rect.midbottom = (int(sx), int(ground_y))
        pygame.draw.rect(surface, colour, rect, border_radius=6)
        pygame.draw.rect(surface, (9, 2, 2), rect, width=2, border_radius=6)
        eye_y = rect.y + rect.height // 3
        pygame.draw.circle(surface, (255, 240, 200), (rect.centerx - rect.width // 5, eye_y), max(2, rect.width // 9))
        pygame.draw.circle(surface, (255, 240, 200), (rect.centerx + rect.width // 5, eye_y), max(2, rect.width // 9))
        if enemy.hp < enemy.max_hp or enemy.stats.boss:
            self._bar(surface, sx, rect.top - 3, max(24, size[0]), enemy.hp / enemy.max_hp, HP_ENEMY)

    def _draw_enemy_sprite(self, surface, enemy, sheet, sx: float, ground_y: float) -> None:
        now = self._now
        uid = enemy.uid
        self._enemy_last[uid] = (sx, enemy.stats.enemy_id)
        if abs(sx - self._enemy_prev_x.get(uid, sx)) > 0.01:
            self._moved_at[uid] = now
        self._enemy_prev_x[uid] = sx
        # no 1x há frames sem passo de simulação: segura o "andando" um instante
        moved = now - self._moved_at.get(uid, -1.0) < WALK_GRACE_SECONDS
        if now < self._attack_until.get(uid, 0.0):
            state, elapsed = "attack", ATTACK_ANIM_SECONDS - (self._attack_until[uid] - now)
        else:
            state, elapsed = "walk", (now if moved else 0.0)
        rect = self._draw_sheet_frame(surface, sheet, state, elapsed, sx, ground_y)
        if enemy.hp < enemy.max_hp or enemy.stats.boss:
            self._bar(surface, sx, rect.top + 10, 34, enemy.hp / enemy.max_hp, HP_ENEMY)

    # ---------------------------------------------------- numeros flutuantes
    def _collect_floaters(self, events, positions) -> None:
        for event in events:
            if event.kind not in ("hit", "heal") or event.target not in positions:
                continue
            x, y = positions[event.target]
            colour = (120, 230, 140) if event.kind == "heal" else (255, 230, 150)
            self.floaters.append([x, y - 10, str(round(event.amount)), colour, 0.7])

    def _draw_floaters(self, surface) -> None:
        font = get_font("consolas", 12, bold=True)
        alive = []
        for f in self.floaters:
            f[1] -= 0.6
            f[4] -= 1 / 30
            if f[4] > 0:
                text = font.render(f[2], True, f[3])
                surface.blit(text, text.get_rect(center=(int(f[0]), int(f[1]))))
                alive.append(f)
        self.floaters = alive[-60:]

    # ------------------------------------------------------------- HUD
    def _draw_hud(self, surface, battle: Battle, mouse_pos) -> None:
        width, height = surface.get_size()
        self._buttons = {}
        title = get_font("consolas", 16, bold=True)
        label = f"Wave {max(1, battle.wave_index + 1)}/{battle.total_waves}"
        if battle.phase == "wave" and battle.is_last_wave:
            label += "  -  CHEFE"
        self._pill(surface, label, (width // 2, 22), title)

        self._button(surface, "speed", f"Velocidade x{self.speed}", (width - 150, height - 30), mouse_pos)
        self._button(surface, "exit", "Abandonar", (width - 150, height - 66), mouse_pos)

        if battle.phase == "between_waves" and self.choices:
            self._draw_cards(surface, mouse_pos)
        elif battle.phase == "between_waves":
            self._banner(surface, "Wave concluída!", "Próxima wave", "next_wave", mouse_pos)
        elif battle.phase == "won":
            self._banner(surface, "VITÓRIA! A defesa resistiu.", "Voltar ao habitat", "finish", mouse_pos)
        elif battle.phase == "lost":
            self._banner(surface, "A nave caiu... tente de novo.", "Voltar ao habitat", "finish", mouse_pos)
        elif battle.phase == "ready":
            self._banner(surface, "Prepare a defesa!", "Iniciar", "next_wave", mouse_pos)

    def _pill(self, surface, text, centre, font) -> None:
        surf = font.render(text, True, TEXT)
        rect = surf.get_rect(center=centre).inflate(24, 10)
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (26, 20, 16, 215), bg.get_rect(), border_radius=rect.height // 2)
        pygame.draw.rect(bg, (9, 2, 2, 235), bg.get_rect(), width=2, border_radius=rect.height // 2)
        surface.blit(bg, rect.topleft)
        surface.blit(surf, surf.get_rect(center=centre))

    def _button(self, surface, key, text, centre, mouse_pos, size=(190, 30)) -> None:
        rect = pygame.Rect(0, 0, *size)
        rect.center = centre
        self._buttons[key] = rect
        hovered = rect.collidepoint(mouse_pos)
        pygame.draw.rect(surface, (130, 92, 60) if hovered else (96, 61, 36), rect, border_radius=8)
        pygame.draw.rect(surface, GOLD if hovered else (157, 130, 98), rect, width=2, border_radius=8)
        font = get_font("consolas", 13, bold=True)
        surf = font.render(text, True, GOLD)
        surface.blit(surf, surf.get_rect(center=rect.center))

    def _banner(self, surface, message, button_text, key, mouse_pos) -> None:
        width, height = surface.get_size()
        font = get_font("consolas", 22, bold=True)
        self._pill(surface, message, (width // 2, height // 2 - 30), font)
        self._button(surface, key, button_text, (width // 2, height // 2 + 20), mouse_pos, size=(240, 40))

    def _draw_cards(self, surface, mouse_pos) -> None:
        width, height = surface.get_size()
        self._pill(surface, "Wave concluída! Escolha uma carta", (width // 2, 58), get_font("consolas", 18, bold=True))
        card_w, card_h, gap = 210, 200, 18
        total = len(self.choices) * card_w + (len(self.choices) - 1) * gap
        x = (width - total) // 2
        top = 90
        name_font = get_font("consolas", 15, bold=True)
        body_font = get_font("consolas", 12)
        tag_font = get_font("consolas", 11, bold=True)
        for card in self.choices:
            rect = pygame.Rect(x, top, card_w, card_h)
            self._buttons[f"card:{card.card_id}"] = rect
            hovered = rect.collidepoint(mouse_pos)
            rare = card.rarity == "rare"
            if hovered:
                rect = rect.move(0, -6)
            pygame.draw.rect(surface, (44, 30, 22), rect, border_radius=12)
            border = (200, 150, 255) if rare else (GOLD if hovered else (157, 130, 98))
            pygame.draw.rect(surface, border, rect, width=3, border_radius=12)
            pygame.draw.rect(surface, (9, 2, 2), rect.inflate(6, 6), width=2, border_radius=14)
            title = name_font.render(card.name, True, GOLD)
            surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 14)))
            for i, line in enumerate(self._wrap(card.description, body_font, card_w - 28)):
                text = body_font.render(line, True, TEXT)
                surface.blit(text, text.get_rect(midtop=(rect.centerx, rect.y + 58 + i * 18)))
            tag = tag_font.render("RARA" if rare else "COMUM", True, border)
            surface.blit(tag, tag.get_rect(midbottom=(rect.centerx, rect.bottom - 10)))
            x += card_w + gap

    @staticmethod
    def _wrap(text: str, font, max_width: int) -> list[str]:
        lines, current = [], ""
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

    def click(self, pos: tuple[int, int]) -> str | None:
        for key, rect in self._buttons.items():
            if rect.collidepoint(pos):
                if key == "speed":
                    self.speed_index = (self.speed_index + 1) % len(SPEEDS)
                return key
        return None
