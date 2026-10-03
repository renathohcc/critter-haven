"""Janela do Álbum: um livro em pixel art (Tkinter Canvas, sem moldura
do Windows) em vez de widgets ttk genéricos. Cada capítulo é um planeta,
cada página uma criatura — não descoberta aparece só como silhueta
preta, descoberta mostra o retrato colorido de verdade (ambos gerados a
partir do spritesheet real em scripts/generate_album_portraits.py).

A janela é "-transparentcolor" (recurso Windows-only do Tk): tudo que
for exatamente TRANSPARENT_KEY vira invisível E clicável-através, então
a silhueta retangular da janela não aparece — só o livro (com cantos
arredondados e a aba de marcador saindo pra fora) fica visível, como se
fosse um objeto flutuando sobre o jogo em vez de "um programa".
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

from critter_haven.config.planets import PLANETS
from critter_haven.core.menu_bridge import MenuBridge
from critter_haven.data.species import load_planet_safe

ASSETS_UI_DIR = Path(__file__).resolve().parent.parent / "assets" / "ui"
CREATURES_DIR = Path(__file__).resolve().parent.parent / "assets" / "creatures"

TRANSPARENT_KEY = "#ff00ff"

BOOK_W, BOOK_H = 480, 680
TAB_MARGIN = 40  # espaço à esquerda do livro reservado pra aba sair
WINDOW_W, WINDOW_H = BOOK_W + TAB_MARGIN, BOOK_H
BOOK_X = TAB_MARGIN

PORTRAIT_BOX = 240  # área (quadrada) reservada pro retrato/silhueta
PORTRAIT_TOP = 180

TEXT_DARK = "#3c2819"
TEXT_MUTED = "#78643d"

RARITY_LABEL = {"common": "Comum", "rare": "Rara", "special": "Especial"}


class AlbumWindow:
    """Segue a mesma interface duck-typed que MenuToplevel (usada pelo
    loop de poll em run_menu_window): window_name, sync_visibility(),
    refresh(snapshot). Não herda de MenuToplevel porque a implementação
    (Canvas puro, sem título, arrastável à mão) é bem diferente das
    janelas ttk comuns."""

    window_name = "album"

    def __init__(self, root: tk.Tk, bridge: MenuBridge) -> None:
        self.bridge = bridge
        self.top = tk.Toplevel(root)
        self.top.overrideredirect(True)
        self.top.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.top.configure(bg=TRANSPARENT_KEY)
        self.top.attributes("-transparentcolor", TRANSPARENT_KEY)
        # sempre por cima -- inclusive da janela do jogo quando ela esta
        # com "Fixar" (always-on-top) ligado; sem isso o livro (uma
        # janela comum) ficava atras do jogo fixado, impossivel de ver.
        self.top.attributes("-topmost", True)
        self.top.withdraw()

        self.canvas = tk.Canvas(
            self.top, width=WINDOW_W, height=WINDOW_H,
            bg=TRANSPARENT_KEY, highlightthickness=0, bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self._chapters = self._load_chapters()
        self.chapter_index = 0
        self.page_index = 0

        self._images: dict[str, tk.PhotoImage] = {}
        self._portrait_cache: dict[tuple[str, bool], tk.PhotoImage] = {}
        self._drag_offset = (0, 0)
        self._last_discovered: bool | None = None

        self._load_static_images()
        self._build_static_scene()
        self._build_page_content()

    @staticmethod
    def _load_chapters() -> list[tuple[str, str, list]]:
        chapters = []
        for planet in PLANETS:
            species_pool = load_planet_safe(planet.id)
            if species_pool:
                chapters.append((planet.id, planet.name, species_pool))
        return chapters

    def _load_static_images(self) -> None:
        for name in ("book_background", "close_x", "arrow_left", "arrow_right", "tab_elyndor"):
            self._images[name] = tk.PhotoImage(file=str(ASSETS_UI_DIR / f"{name}.png"))

    def _build_static_scene(self) -> None:
        c = self.canvas
        bg_item = c.create_image(BOOK_X, 0, image=self._images["book_background"], anchor="nw")

        # arrastar a janela clicando em qualquer parte do livro que nao
        # seja um botao. Precisa ser bindado na PROPRIA imagem de fundo
        # (nao num retangulo invisivel por baixo dela) -- o Tkinterso
        # entrega o evento pro item mais no topo sob o cursor, e um
        # retangulo com fill="" nem sequer registra clique nenhum; um
        # botao por cima (seta/X/aba), por ter seu proprio bind, ainda
        # tem prioridade sobre esse.
        c.tag_bind(bg_item, "<ButtonPress-1>", self._start_drag)
        c.tag_bind(bg_item, "<B1-Motion>", self._on_drag)

        # aba de marcador do capitulo (soh Elyndor por enquanto, mas a
        # lista suporta mais no futuro -- cada aba fica empilhada na
        # lateral esquerda do livro)
        self.tab_items: list[int] = []
        for i, (planet_id, _name, _pool) in enumerate(self._chapters):
            tab_y = 110 + i * 90
            tab_x = BOOK_X - 36
            item = c.create_image(tab_x, tab_y, image=self._images["tab_elyndor"], anchor="nw")
            c.tag_bind(item, "<Button-1>", lambda _e, idx=i: self._select_chapter(idx))
            self.tab_items.append(item)

        close_item = c.create_image(
            BOOK_X + BOOK_W - 34, 14, image=self._images["close_x"], anchor="nw"
        )
        c.tag_bind(close_item, "<Button-1>", lambda _e: self._on_close())

        arrow_y = 605
        left_item = c.create_image(
            BOOK_X + BOOK_W // 2 - 110, arrow_y, image=self._images["arrow_left"], anchor="center"
        )
        right_item = c.create_image(
            BOOK_X + BOOK_W // 2 + 110, arrow_y, image=self._images["arrow_right"], anchor="center"
        )
        c.tag_bind(left_item, "<Button-1>", lambda _e: self._change_page(-1))
        c.tag_bind(right_item, "<Button-1>", lambda _e: self._change_page(1))

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_offset = (event.x_root - self.top.winfo_x(), event.y_root - self.top.winfo_y())

    def _on_drag(self, event: tk.Event) -> None:
        ox, oy = self._drag_offset
        self.top.geometry(f"+{event.x_root - ox}+{event.y_root - oy}")

    def _on_close(self) -> None:
        self.bridge.play_sfx("ui_click")
        self.bridge.hide_window(self.window_name)
        self.top.withdraw()

    def _select_chapter(self, index: int) -> None:
        if index == self.chapter_index:
            return
        self.bridge.play_sfx("ui_click")
        self.chapter_index = index
        self.page_index = 0
        self._build_page_content()

    def _change_page(self, delta: int) -> None:
        if not self._chapters:
            return
        _planet_id, _name, species_pool = self._chapters[self.chapter_index]
        count = len(species_pool)
        if count == 0:
            return
        self.bridge.play_sfx("ui_click")
        self.page_index = (self.page_index + delta) % count
        self._build_page_content()

    def _get_portrait_image(self, species_id: str, discovered: bool) -> tk.PhotoImage:
        key = (species_id, discovered)
        if key not in self._portrait_cache:
            subdir = "portraits" if discovered else "silhouettes"
            path = CREATURES_DIR / subdir / f"{species_id}.png"
            img = tk.PhotoImage(file=str(path))
            zoom = max(2, PORTRAIT_BOX // img.width())
            self._portrait_cache[key] = img.zoom(zoom, zoom)
        return self._portrait_cache[key]

    def _build_page_content(self) -> None:
        """(Re)desenha só o conteúdo dinâmico da página atual — remove os
        itens da página anterior (tag "page") e cria os novos por cima
        do plano de fundo estático do livro."""
        c = self.canvas
        c.delete("page")

        if not self._chapters:
            c.create_text(
                BOOK_X + BOOK_W // 2, 300, text="Nenhum capítulo disponível ainda.",
                font=("Consolas", 14), fill=TEXT_MUTED, tags="page",
            )
            return

        planet_id, planet_name, species_pool = self._chapters[self.chapter_index]
        species = species_pool[self.page_index]
        discovered = self._is_discovered(planet_id, species.id)
        self._last_discovered = discovered

        cx = BOOK_X + BOOK_W // 2

        c.create_text(
            cx, 40, text=planet_name.upper(), font=("Consolas", 22, "bold"),
            fill=TEXT_DARK, tags="page",
        )

        portrait = self._get_portrait_image(species.id, discovered)
        portrait_y = PORTRAIT_TOP + (PORTRAIT_BOX - portrait.height()) // 2
        c.create_image(cx, portrait_y, image=portrait, anchor="n", tags="page")
        # mantem referencia viva (senao o Tk descarta a imagem do canvas)
        c.portrait_ref = portrait

        info_y = PORTRAIT_TOP + PORTRAIT_BOX + 30
        if discovered:
            rarity = RARITY_LABEL.get(species.rarity, species.rarity)
            c.create_text(
                cx, info_y, text=f"{species.name}  ({rarity})",
                font=("Consolas", 20, "bold"), fill=TEXT_DARK, tags="page",
            )
            c.create_text(
                cx, info_y + 30,
                text=f"Produção: {species.base_gold_per_second} ouro/s",
                font=("Consolas", 13), fill=TEXT_DARK, tags="page",
            )
            c.create_text(
                cx, info_y + 52, text=f"Item: {species.item_name}",
                font=("Consolas", 13), fill=TEXT_DARK, tags="page",
            )
            for i, line in enumerate(_wrap_text(species.description, 42)):
                c.create_text(
                    cx, info_y + 82 + i * 20, text=line,
                    font=("Consolas", 13), fill=TEXT_MUTED, tags="page",
                )
        else:
            c.create_text(
                cx, info_y, text="???", font=("Consolas", 20, "bold"),
                fill=TEXT_DARK, tags="page",
            )
            c.create_text(
                cx, info_y + 34, text="Ainda não descoberta",
                font=("Consolas", 13), fill=TEXT_MUTED, tags="page",
            )

        c.create_text(
            cx, 605, text=f"{self.page_index + 1} / {len(species_pool)}",
            font=("Consolas", 15, "bold"), fill=TEXT_DARK, tags="page",
        )

    def _is_discovered(self, planet_id: str, species_id: str) -> bool:
        snapshot = self.bridge.read_snapshot()
        album = snapshot.get("album", {})
        planet_info = album.get(planet_id)
        if not planet_info:
            return False
        for entry in planet_info["species"]:
            if entry["id"] == species_id:
                return entry["discovered"]
        return False

    def sync_visibility(self) -> None:
        should_show = self.bridge.is_window_visible(self.window_name)
        is_mapped = bool(self.top.winfo_ismapped())
        if should_show and not is_mapped:
            self.top.deiconify()
            self.top.lift()
        elif not should_show and is_mapped:
            self.top.withdraw()

    def refresh(self, _snapshot: dict) -> None:
        # o conteudo da pagina atual só precisa ser redesenhado quando o
        # jogador vira a pagina (ja tratado em _change_page/
        # _select_chapter) OU quando a criatura da pagina aberta acaba de
        # ser descoberta enquanto o livro esta aberto -- nesse segundo
        # caso ninguem mais chama _build_page_content, entao checamos
        # aqui a cada poll (barato: 1 lookup) se o status mudou.
        if not self._chapters:
            return
        planet_id, _name, species_pool = self._chapters[self.chapter_index]
        species = species_pool[self.page_index]
        if self._is_discovered(planet_id, species.id) != self._last_discovered:
            self._build_page_content()


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines
