"""Menu inicial do jogo, desenhado direto na janela do pygame por cima do
habitat. Só cuida de layout/desenho/cliques e devolve a ação escolhida
("continue", "new", "settings", "quit") — quem decide o que fazer com
ela é o App."""

from __future__ import annotations

import pygame

from critter_haven.render.fonts import get_font
from critter_haven.render.ui_icons import ASSETS_UI_DIR

# Editar aqui pra mudar os créditos exibidos.
CREDITS_LINES = (
    "Critter Haven: Homie's Journey",
    "",
    "Desenvolvimento: renatho",
    "Programação assistida por Claude Code",
    "",
    "Criaturas: PixelLab",
    "UI, ícones e logo: Aseprite",
    "Cenário: GandalfHardcore FREE Platformer Assets (itch.io)",
    "Mapa: Tiled  -  Engine: Python + pygame-ce",
    "Música e efeitos sonoros: gerados por IA",
)

TEXT_GOLD = (244, 214, 147)
TEXT_CREAM = (230, 214, 178)
BUTTON_SIZE = (280, 50)
BUTTON_GAP = (20, 10)

_image_cache: dict[str, pygame.Surface] = {}


def _image(name: str) -> pygame.Surface:
    if name not in _image_cache:
        _image_cache[name] = pygame.image.load(str(ASSETS_UI_DIR / f"{name}.png")).convert_alpha()
    return _image_cache[name]


class StartMenu:
    def __init__(self, has_save: bool) -> None:
        self.has_save = has_save
        self.view = "main"  # "main" | "credits" | "confirm_new"
        self._buttons: list[tuple[str, str, pygame.Rect]] = []

    def _layout(self, size: tuple[int, int]) -> list[tuple[str, str, pygame.Rect]]:
        width, height = size
        bw, bh = BUTTON_SIZE
        gx, gy = BUTTON_GAP

        if self.view == "confirm_new":
            panel = self._panel_rect(size)
            y = panel.bottom - 90
            cw = 230  # dois botoes lado a lado precisam caber dentro do painel
            return [
                ("confirm_yes", "Sim, apagar", pygame.Rect(panel.centerx - cw - gx // 2, y, cw, bh)),
                ("confirm_no", "Cancelar", pygame.Rect(panel.centerx + gx // 2, y, cw, bh)),
            ]
        if self.view == "credits":
            panel = self._panel_rect(size)
            return [("credits_back", "Voltar", pygame.Rect(panel.centerx - bw // 2, panel.bottom - 80, bw, bh))]

        entries = []
        if self.has_save:
            entries.append(("continue", "Continuar"))
        entries += [("new", "Novo Jogo"), ("settings", "Configurações"), ("credits", "Créditos"), ("quit", "Sair")]

        top = 200
        rects = []
        for i, (action, label) in enumerate(entries):
            row, col = divmod(i, 2)
            in_last_odd = i == len(entries) - 1 and len(entries) % 2 == 1
            if in_last_odd:
                x = width // 2 - bw // 2
            else:
                x = width // 2 + (-bw - gx // 2 if col == 0 else gx // 2)
            rects.append((action, label, pygame.Rect(x, top + row * (bh + gy), bw, bh)))
        return rects

    def _panel_rect(self, size: tuple[int, int]) -> pygame.Rect:
        panel = _image("menu_panel")
        rect = panel.get_rect()
        rect.center = (size[0] // 2, size[1] // 2 + 5)
        return rect

    def _button_at(self, pos: tuple[int, int]) -> str | None:
        for action, _label, rect in self._buttons:
            if rect.collidepoint(pos):
                return action
        return None

    def click(self, pos: tuple[int, int]) -> str | None:
        action = self._button_at(pos)
        if action is None:
            return None
        if action == "new":
            if self.has_save:
                self.view = "confirm_new"
                return "ui"
            return "new"
        if action == "confirm_yes":
            self.view = "main"
            return "new"
        if action in ("confirm_no", "credits_back"):
            self.view = "main"
            return "ui"
        if action == "credits":
            self.view = "credits"
            return "ui"
        return action

    def draw(self, surface: pygame.Surface, mouse_pos: tuple[int, int]) -> None:
        width, height = surface.get_size()
        dim = pygame.Surface((width, height), pygame.SRCALPHA)
        dim.fill((10, 8, 14, 110))
        surface.blit(dim, (0, 0))

        self._buttons = self._layout((width, height))

        if self.view == "main":
            logo = _image("logo")
            surface.blit(logo, logo.get_rect(midtop=(width // 2, 18)))
        else:
            panel = self._panel_rect((width, height))
            surface.blit(_image("menu_panel"), panel)
            if self.view == "credits":
                self._draw_credits(surface, panel)
            else:
                self._draw_confirm(surface, panel)

        font = get_font("consolas", 20, bold=True)
        for action, label, rect in self._buttons:
            hovered = rect.collidepoint(mouse_pos)
            image = _image("menu_button_hover" if hovered else "menu_button")
            if image.get_size() != rect.size:
                image = pygame.transform.scale(image, rect.size)
            surface.blit(image, rect)
            text = font.render(label, True, TEXT_GOLD)
            surface.blit(text, text.get_rect(center=(rect.centerx, rect.centery - 1)))

    def _draw_credits(self, surface: pygame.Surface, panel: pygame.Rect) -> None:
        title_font = get_font("consolas", 20, bold=True)
        font = get_font("consolas", 13)
        y = panel.top + 34
        for i, line in enumerate(CREDITS_LINES):
            if not line:
                y += 8
                continue
            f = title_font if i == 0 else font
            color = TEXT_GOLD if i == 0 else TEXT_CREAM
            text = f.render(line, True, color)
            surface.blit(text, text.get_rect(midtop=(panel.centerx, y)))
            y += text.get_height() + 4

    def _draw_confirm(self, surface: pygame.Surface, panel: pygame.Rect) -> None:
        title_font = get_font("consolas", 20, bold=True)
        font = get_font("consolas", 14)
        title = title_font.render("Começar um novo jogo?", True, TEXT_GOLD)
        surface.blit(title, title.get_rect(midtop=(panel.centerx, panel.top + 60)))
        for i, line in enumerate(("Todo o progresso salvo (criaturas, ouro,", "upgrades e álbum) será apagado.")):
            text = font.render(line, True, TEXT_CREAM)
            surface.blit(text, text.get_rect(midtop=(panel.centerx, panel.top + 110 + i * 22)))
