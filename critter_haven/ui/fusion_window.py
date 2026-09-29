"""Janela de Fusão: um altar (Tkinter Canvas, sem moldura do Windows,
mesma técnica do Álbum/Baú/Upgrades/Nave) — um cristal central com 2
slots que mostram o retrato de quem foi escolhido, uma lista clicável
de criaturas vivas (rola com a roda do mouse quando não cabe tudo) e um
botão "Fundir" que só habilita com os 2 slots preenchidos.

A lista roda dentro de um Canvas FILHO com tamanho fixo (não o canvas
principal da janela) — é a forma correta de garantir que os cards de
criatura nunca vazem pra fora do painel roxo-escuro por baixo do
cristal, mesmo com muitas criaturas: o Tkinter recorta automaticamente
qualquer conteúdo fora dos limites de um widget Canvas.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

from critter_haven.core.menu_bridge import MenuBridge

ASSETS_UI_DIR = Path(__file__).resolve().parent.parent / "assets" / "ui"
PORTRAITS_DIR = Path(__file__).resolve().parent.parent / "assets" / "creatures" / "portraits"

TRANSPARENT_KEY = "#ff00ff"
WINDOW_W, WINDOW_H = 440, 720

GOLD = "#f4d693"
TITLE_COLOR = "#f4d693"
NAME_COLOR = "#dcd2eb"
RARITY_COLOR = "#968cb4"
RESULT_COLOR = "#e6d2ff"
ALTAR_BG = "#1e142e"
ROW_BG = "#140e20"
ROW_BG_SELECTED = "#5a4082"
ROW_OUTLINE = "#46375f"

SLOT_Y = 210
SLOT_R = 34
SLOT_OFFSET_X = 80
ICON_BOX = 40

LIST_PANEL = (24, 274, 411, 566)  # x0, y0, x1, y1 (com pequeno inset da arte)
ROW_H = 54
ROW_GAP = 6
ROW_PITCH = ROW_H + ROW_GAP

FUNDIR_BTN_Y = 600
RESULT_Y = 668


class FusionWindow:
    """Mesma interface duck-typed usada por run_menu_window: window_name,
    sync_visibility(), refresh(snapshot)."""

    window_name = "fusion"

    def __init__(self, root: tk.Tk, bridge: MenuBridge) -> None:
        self.bridge = bridge
        self.top = tk.Toplevel(root)
        self.top.overrideredirect(True)
        self.top.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.top.configure(bg=TRANSPARENT_KEY)
        self.top.attributes("-transparentcolor", TRANSPARENT_KEY)
        self.top.attributes("-topmost", True)
        self.top.withdraw()

        self.canvas = tk.Canvas(
            self.top, width=WINDOW_W, height=WINDOW_H,
            bg=TRANSPARENT_KEY, highlightthickness=0, bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self._images: dict[str, tk.PhotoImage] = {}
        self._portrait_cache: dict[str, tk.PhotoImage] = {}
        self._drag_offset = (0, 0)

        self._creatures: list[dict] = []  # ultimo snapshot["creatures"]
        self._selected_ids: list[int] = []
        self._last_creature_ids: list[int] | None = None

        self._load_images()
        self._build_static_scene()
        self._build_list_canvas()

    def _load_images(self) -> None:
        for name in ("altar_background", "fundir_button", "close_x"):
            self._images[name] = tk.PhotoImage(file=str(ASSETS_UI_DIR / f"{name}.png"))

    def _get_portrait(self, species_id: str) -> tk.PhotoImage:
        if species_id not in self._portrait_cache:
            img = tk.PhotoImage(file=str(PORTRAITS_DIR / f"{species_id}.png"))
            width = img.width()
            if width <= ICON_BOX:
                zoom = max(1, ICON_BOX // width)
                if zoom > 1:
                    img = img.zoom(zoom, zoom)
            else:
                factor = -(-width // ICON_BOX)  # ceil division
                img = img.subsample(factor, factor)
            self._portrait_cache[species_id] = img
        return self._portrait_cache[species_id]

    def _build_static_scene(self) -> None:
        c = self.canvas
        bg_item = c.create_image(0, 0, image=self._images["altar_background"], anchor="nw")
        c.tag_bind(bg_item, "<ButtonPress-1>", self._start_drag)
        c.tag_bind(bg_item, "<B1-Motion>", self._on_drag)

        c.create_text(
            WINDOW_W // 2, 16, text="FUSÃO", font=("Consolas", 20, "bold"),
            fill=TITLE_COLOR, anchor="n",
        )

        close_item = c.create_image(WINDOW_W - 52, 12, image=self._images["close_x"], anchor="nw")
        c.tag_bind(close_item, "<Button-1>", lambda _e: self._on_close())

        # slots (2): circulo vazio ou retrato da criatura escolhida
        self.slot_items: list[dict] = []
        for i in range(2):
            cx = WINDOW_W // 2 + (-SLOT_OFFSET_X if i == 0 else SLOT_OFFSET_X)
            ring = c.create_oval(
                cx - SLOT_R, SLOT_Y - SLOT_R, cx + SLOT_R, SLOT_Y + SLOT_R,
                fill=ALTAR_BG, outline=GOLD, width=3,
            )
            placeholder = c.create_text(
                cx, SLOT_Y, text="?", font=("Consolas", 22, "bold"), fill=RARITY_COLOR,
            )
            self.slot_items.append({"cx": cx, "ring": ring, "placeholder": placeholder, "portrait": None})

        btn_x = (WINDOW_W - self._images["fundir_button"].width()) // 2
        self.fundir_btn_item = c.create_image(
            btn_x, FUNDIR_BTN_Y, image=self._images["fundir_button"], anchor="nw"
        )
        self.fundir_text_item = c.create_text(
            WINDOW_W // 2, FUNDIR_BTN_Y + self._images["fundir_button"].height() // 2,
            text="FUNDIR", font=("Consolas", 15, "bold"), fill=RARITY_COLOR,
        )
        c.tag_bind(self.fundir_btn_item, "<Button-1>", lambda _e: self._on_fundir())
        c.tag_bind(self.fundir_text_item, "<Button-1>", lambda _e: self._on_fundir())

        self.result_text_item = c.create_text(
            WINDOW_W // 2, RESULT_Y, text="", font=("Consolas", 11), fill=RESULT_COLOR,
            width=WINDOW_W - 60, justify="center",
        )

    def _build_list_canvas(self) -> None:
        x0, y0, x1, y1 = LIST_PANEL
        width, height = x1 - x0, y1 - y0
        self.list_canvas = tk.Canvas(
            self.top, width=width, height=height, bg=ALTAR_BG, highlightthickness=0, bd=0,
        )
        self.canvas.create_window(x0, y0, window=self.list_canvas, anchor="nw")
        self.list_canvas.configure(yscrollincrement=ROW_PITCH)
        self.list_canvas.bind(
            "<MouseWheel>",
            lambda e: self.list_canvas.yview_scroll(-1 * (e.delta // 120), "units"),
        )
        self._list_panel_size = (width, height)

    def _rebuild_list(self) -> None:
        lc = self.list_canvas
        lc.delete("all")
        width, panel_height = self._list_panel_size
        row_width = width - 16

        y = 6
        for entry in self._creatures:
            cid = entry["id"]
            selected = cid in self._selected_ids
            fill = ROW_BG_SELECTED if selected else ROW_BG
            outline = GOLD if selected else ROW_OUTLINE

            row_tag = f"row{cid}"
            lc.create_rectangle(
                8, y, 8 + row_width, y + ROW_H, fill=fill, outline=outline, width=2,
                tags=row_tag,
            )
            portrait = self._get_portrait(entry["species_id"])
            icon_x = 8 + 10 + (ICON_BOX - portrait.width()) // 2
            icon_y = y + (ROW_H - portrait.height()) // 2
            lc.create_image(icon_x, icon_y, image=portrait, anchor="nw", tags=row_tag)

            text_x = 8 + 10 + ICON_BOX + 12
            lc.create_text(
                text_x, y + 10, text=entry["name"], anchor="nw",
                font=("Consolas", 13, "bold"), fill=NAME_COLOR, tags=row_tag,
            )
            lc.create_text(
                text_x, y + 30, text=entry["rarity"], anchor="nw",
                font=("Consolas", 10), fill=RARITY_COLOR, tags=row_tag,
            )

            # tag cobrindo retangulo+icone+textos -- clicar em qualquer
            # parte da linha (nao so o fundo) conta como selecionar
            lc.tag_bind(row_tag, "<Button-1>", lambda _e, c=cid: self._toggle_selection(c))

            y += ROW_PITCH

        content_height = max(y, panel_height)
        lc.configure(scrollregion=(0, 0, width, content_height))

    def _toggle_selection(self, creature_id: int) -> None:
        if creature_id in self._selected_ids:
            self._selected_ids.remove(creature_id)
        else:
            self._selected_ids.append(creature_id)
            if len(self._selected_ids) > 2:
                self._selected_ids.pop(0)
        self._rebuild_list()
        self._update_slots()

    def _update_slots(self) -> None:
        c = self.canvas
        by_id = {entry["id"]: entry for entry in self._creatures}
        for i, slot in enumerate(self.slot_items):
            creature_id = self._selected_ids[i] if i < len(self._selected_ids) else None
            if slot["portrait"] is not None:
                c.delete(slot["portrait"])
                slot["portrait"] = None
            if creature_id is not None and creature_id in by_id:
                entry = by_id[creature_id]
                portrait = self._get_portrait(entry["species_id"])
                c.itemconfig(slot["placeholder"], text="")
                slot["portrait"] = c.create_image(
                    slot["cx"], SLOT_Y, image=portrait, anchor="center"
                )
            else:
                c.itemconfig(slot["placeholder"], text="?")

        can_fuse = len(self._selected_ids) == 2
        c.itemconfig(self.fundir_text_item, fill=GOLD if can_fuse else RARITY_COLOR)
        self._can_fuse = can_fuse

    def _on_fundir(self) -> None:
        if not getattr(self, "_can_fuse", False):
            return
        id_a, id_b = self._selected_ids
        self.bridge.push_command("fuse", (id_a, id_b))
        self._selected_ids = []
        self._rebuild_list()
        self._update_slots()

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_offset = (event.x_root - self.top.winfo_x(), event.y_root - self.top.winfo_y())

    def _on_drag(self, event: tk.Event) -> None:
        ox, oy = self._drag_offset
        self.top.geometry(f"+{event.x_root - ox}+{event.y_root - oy}")

    def _on_close(self) -> None:
        self.bridge.hide_window(self.window_name)
        self.top.withdraw()

    def sync_visibility(self) -> None:
        should_show = self.bridge.is_window_visible(self.window_name)
        is_mapped = bool(self.top.winfo_ismapped())
        if should_show and not is_mapped:
            self.top.deiconify()
            self.top.lift()
        elif not should_show and is_mapped:
            self.top.withdraw()

    def refresh(self, snapshot: dict) -> None:
        creatures = snapshot.get("creatures", [])
        ids = [entry["id"] for entry in creatures]
        if ids != self._last_creature_ids:
            self._last_creature_ids = ids
            self._creatures = creatures
            # criaturas que sumiram (fundidas/vendidas em outro fluxo) saem
            # da selecao, senao o botao Fundir ficaria "pronto" com um id
            # que nao existe mais
            self._selected_ids = [i for i in self._selected_ids if i in ids]
            self._rebuild_list()
            self._update_slots()

        result = snapshot.get("last_fusion_result")
        if result:
            self.canvas.itemconfig(self.result_text_item, text=result)
