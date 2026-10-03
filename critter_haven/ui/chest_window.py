"""Janela do Baú: um baú de tesouro aberto (Tkinter Canvas, sem moldura
do Windows, mesma técnica do Álbum) listando os itens separados por
criatura — o jogador escolhe a quantidade com um seletor -/+ e vende
exatamente o quanto quiser de cada item, em vez de só "vender tudo de
uma vez".

Ouro e contagem de criaturas não aparecem mais aqui (já ficam na HUD
principal do jogo) e os controles de janela (Tamanho/Fixar) mudaram pra
janela de Configurações — ver critter_haven/ui/menu_window.py
(ConfigWindow).

Os ícones de item ainda são um placeholder (o retrato da própria
criatura que produz o item) até existir sprite de item de verdade
gerado no PixelLab.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

from critter_haven.core.menu_bridge import MenuBridge

ASSETS_UI_DIR = Path(__file__).resolve().parent.parent / "assets" / "ui"
PORTRAITS_DIR = Path(__file__).resolve().parent.parent / "assets" / "creatures" / "portraits"
ITEMS_DIR = Path(__file__).resolve().parent.parent / "assets" / "items"

TRANSPARENT_KEY = "#ff00ff"
WINDOW_W, WINDOW_H = 460, 700

GOLD = "#f4d693"
GOLD_DIM = "#8a7a5c"
TITLE_COLOR = "#f4d693"

ROW_Y_START = 120
ROW_PITCH = 108
ICON_BOX = 36

# coordenadas relativas ao canto superior-esquerdo de cada placa (380x92)
STEPPER_Y = 30
MINUS_CX = 254
QTY_CX = 300
PLUS_CX = 346
SELL_BTN_X = 252
SELL_BTN_Y = 52


class ChestWindow:
    """Mesma interface duck-typed usada por run_menu_window: window_name,
    sync_visibility(), refresh(snapshot)."""

    window_name = "bau"

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
        # item_name -> quantidade selecionada no seletor (persiste entre
        # refreshes, so eh reclampada quando o estoque muda)
        self._quantities: dict[str, int] = {}
        self._row_items: list[dict] = []
        self._last_item_names: list[str] | None = None

        self._load_images()
        self._build_static_scene()

    def _load_images(self) -> None:
        for name in (
            "chest_panel_background", "item_plaque_bg", "sell_button",
            "stepper_button", "close_x",
        ):
            self._images[name] = tk.PhotoImage(file=str(ASSETS_UI_DIR / f"{name}.png"))

    def _get_item_icon(self, species_id: str) -> tk.PhotoImage:
        """Ícone do item de verdade (assets/items/<id>.png) quando já foi
        gerado no PixelLab; senão cai pro retrato da própria criatura
        como placeholder (Fase 8.6 — vai sumindo item por item conforme
        o dev for gerando os sprites de verdade)."""
        if species_id not in self._portrait_cache:
            item_path = ITEMS_DIR / f"{species_id}.png"
            source_path = item_path if item_path.exists() else PORTRAITS_DIR / f"{species_id}.png"
            img = tk.PhotoImage(file=str(source_path))
            width = img.width()
            if width <= ICON_BOX:
                zoom = max(1, ICON_BOX // width)
                if zoom > 1:
                    img = img.zoom(zoom, zoom)
            else:
                # criaturas/itens maiores precisam encolher pra caber na
                # caixa do icone -- senao vaza por cima do nome do item.
                factor = -(-width // ICON_BOX)  # ceil division
                img = img.subsample(factor, factor)
            self._portrait_cache[species_id] = img
        return self._portrait_cache[species_id]

    def _build_static_scene(self) -> None:
        c = self.canvas
        bg_item = c.create_image(
            0, 0, image=self._images["chest_panel_background"], anchor="nw"
        )
        c.tag_bind(bg_item, "<ButtonPress-1>", self._start_drag)
        c.tag_bind(bg_item, "<B1-Motion>", self._on_drag)

        c.create_text(
            WINDOW_W // 2, 40, text="BAÚ", font=("Consolas", 22, "bold"), fill=TITLE_COLOR,
        )

        close_item = c.create_image(WINDOW_W - 54, 14, image=self._images["close_x"], anchor="nw")
        c.tag_bind(close_item, "<Button-1>", lambda _e: self._on_close())

    def _rebuild_rows(self, items: list[dict]) -> None:
        c = self.canvas
        c.delete("row")

        plaque = self._images["item_plaque_bg"]
        stepper = self._images["stepper_button"]
        sell_btn = self._images["sell_button"]
        row_x = (WINDOW_W - plaque.width()) // 2

        self._row_items = []
        row_y = ROW_Y_START
        for entry in items:
            item_name = entry["item_name"]
            self._quantities.setdefault(item_name, 1)

            c.create_image(row_x, row_y, image=plaque, anchor="nw", tags="row")

            portrait = self._get_item_icon(entry["species_id"])
            icon_y = row_y + (plaque.height() - portrait.height()) // 2
            c.create_image(row_x + 12, icon_y, image=portrait, anchor="nw", tags="row")

            c.create_text(
                row_x + 54, row_y + 16, text=entry["species_name"], anchor="nw",
                font=("Consolas", 14, "bold"), fill=GOLD, tags="row",
            )
            count_text_item = c.create_text(
                row_x + 54, row_y + 42, text="", anchor="nw",
                font=("Consolas", 11), fill=GOLD_DIM, tags="row",
            )

            minus_item = c.create_image(
                row_x + MINUS_CX, row_y + STEPPER_Y, image=stepper, anchor="center", tags="row"
            )
            c.create_text(
                row_x + MINUS_CX, row_y + STEPPER_Y, text="-",
                font=("Consolas", 14, "bold"), fill=GOLD, tags="row",
            )
            qty_text_item = c.create_text(
                row_x + QTY_CX, row_y + STEPPER_Y, text="1",
                font=("Consolas", 14, "bold"), fill=GOLD, tags="row",
            )
            plus_item = c.create_image(
                row_x + PLUS_CX, row_y + STEPPER_Y, image=stepper, anchor="center", tags="row"
            )
            c.create_text(
                row_x + PLUS_CX, row_y + STEPPER_Y, text="+",
                font=("Consolas", 14, "bold"), fill=GOLD, tags="row",
            )

            sell_item = c.create_image(
                row_x + SELL_BTN_X, row_y + SELL_BTN_Y, image=sell_btn, anchor="nw", tags="row"
            )
            sell_text_item = c.create_text(
                row_x + SELL_BTN_X + sell_btn.width() // 2,
                row_y + SELL_BTN_Y + sell_btn.height() // 2,
                text="Vender", font=("Consolas", 12, "bold"), fill=GOLD, tags="row",
            )

            c.tag_bind(minus_item, "<Button-1>", lambda _e, n=item_name: self._adjust_qty(n, -1))
            c.tag_bind(plus_item, "<Button-1>", lambda _e, n=item_name: self._adjust_qty(n, 1))
            c.tag_bind(sell_item, "<Button-1>", lambda _e, n=item_name: self._sell(n))
            c.tag_bind(sell_text_item, "<Button-1>", lambda _e, n=item_name: self._sell(n))

            self._row_items.append(
                {
                    "item_name": item_name,
                    "count": 0,
                    "count_text_item": count_text_item,
                    "qty_text_item": qty_text_item,
                    "sell_text_item": sell_text_item,
                }
            )
            row_y += ROW_PITCH

    def _row_by_name(self, item_name: str) -> dict | None:
        for row in self._row_items:
            if row["item_name"] == item_name:
                return row
        return None

    def _adjust_qty(self, item_name: str, delta: int) -> None:
        row = self._row_by_name(item_name)
        if row is None or row["count"] <= 0:
            return
        qty = self._quantities.get(item_name, 1) + delta
        qty = max(1, min(qty, row["count"]))
        self.bridge.play_sfx("ui_click")
        self._quantities[item_name] = qty
        self.canvas.itemconfig(row["qty_text_item"], text=str(qty))

    def _sell(self, item_name: str) -> None:
        row = self._row_by_name(item_name)
        if row is None or row["count"] <= 0:
            self.bridge.play_sfx("denied")
            return
        quantity = self._quantities.get(item_name, 1)
        self.bridge.push_command("sell_item", (item_name, quantity))

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_offset = (event.x_root - self.top.winfo_x(), event.y_root - self.top.winfo_y())

    def _on_drag(self, event: tk.Event) -> None:
        ox, oy = self._drag_offset
        self.top.geometry(f"+{event.x_root - ox}+{event.y_root - oy}")

    def _on_close(self) -> None:
        self.bridge.play_sfx("ui_click")
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
        items = snapshot.get("chest_items")
        if items is None:
            return

        names = [entry["item_name"] for entry in items]
        if names != self._last_item_names:
            self._last_item_names = names
            self._rebuild_rows(items)

        c = self.canvas
        for entry, row in zip(items, self._row_items):
            count = entry["count"]
            row["count"] = count
            c.itemconfig(
                row["count_text_item"],
                text=f"{count} un.  ({entry['price']:.1f}/un.)",
            )

            # reclampa a quantidade selecionada se o estoque encolheu
            # (ex: vendeu em outra instancia, ou o item acabou)
            item_name = entry["item_name"]
            qty = self._quantities.get(item_name, 1)
            clamped = max(1, min(qty, count)) if count > 0 else 1
            if clamped != qty:
                self._quantities[item_name] = clamped
                c.itemconfig(row["qty_text_item"], text=str(clamped))

            has_stock = count > 0
            c.itemconfig(row["sell_text_item"], fill=GOLD if has_stock else GOLD_DIM)
