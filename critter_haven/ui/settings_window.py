"""Janela de Configurações: painel metálico (Tkinter Canvas, sem
moldura do Windows, mesma técnica das outras) com parafusos nos cantos
— combina com o ícone de engrenagem. Reúne Tamanho/Fixar (antes vivam
dentro do Baú) e já reserva espaço pra futuras opções de áudio/música.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path

from critter_haven.core.menu_bridge import MenuBridge

ASSETS_UI_DIR = Path(__file__).resolve().parent.parent / "assets" / "ui"

TRANSPARENT_KEY = "#ff00ff"
WINDOW_W, WINDOW_H = 440, 460

GOLD = "#f4d693"
TITLE_COLOR = "#f4d693"
LABEL_COLOR = "#dcdce1"
CAPTION_COLOR = "#78787f"
LABEL_DIM = "#6e6e75"

ROW_Y_START = 66
ROW_PITCH = 96

SWITCH_ON_COLOR = "#78be78"
SWITCH_OFF_COLOR = "#46464c"
SWITCH_KNOB = "#f5f5eb"
SWITCH_OUTLINE = "#0a0505"
SWITCH_W, SWITCH_H = 70, 34


class SettingsWindow:
    """Mesma interface duck-typed usada por run_menu_window: window_name,
    sync_visibility(), refresh(snapshot)."""

    window_name = "config"

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
        self._drag_offset = (0, 0)
        self._pin_on = False

        self._load_images()
        self._build_scene()

    @staticmethod
    def _fit_text(family: str, size: int, weight: str, text: str, max_width: int) -> tuple[str, int]:
        """Mesma blindagem usada nos outros menus: encolhe a fonte (ate um
        piso) e, se ainda assim nao coubesse, trunca com reticencias --
        evita que a legenda invada o botao ao lado."""
        size_floor = 9
        s = size
        while s >= size_floor:
            f = tkfont.Font(family=family, size=s, weight=weight)
            if f.measure(text) <= max_width:
                return text, s
            s -= 1
        f = tkfont.Font(family=family, size=size_floor, weight=weight)
        truncated = text
        while truncated and f.measure(truncated + "…") > max_width:
            truncated = truncated[:-1]
        return (f"{truncated}…" if truncated != text else text), size_floor

    def _load_images(self) -> None:
        for name in ("settings_background", "settings_row_bg", "buy_button", "close_x"):
            self._images[name] = tk.PhotoImage(file=str(ASSETS_UI_DIR / f"{name}.png"))

    def _build_scene(self) -> None:
        c = self.canvas
        bg_item = c.create_image(0, 0, image=self._images["settings_background"], anchor="nw")
        c.tag_bind(bg_item, "<ButtonPress-1>", self._start_drag)
        c.tag_bind(bg_item, "<B1-Motion>", self._on_drag)

        c.create_text(
            WINDOW_W // 2, 16, text="CONFIGURAÇÕES", font=("Consolas", 18, "bold"),
            fill=TITLE_COLOR, anchor="n",
        )

        close_item = c.create_image(WINDOW_W - 52, 12, image=self._images["close_x"], anchor="nw")
        c.tag_bind(close_item, "<Button-1>", lambda _e: self._on_close())

        row_bg = self._images["settings_row_bg"]
        buy_btn = self._images["buy_button"]
        row_x = (WINDOW_W - row_bg.width()) // 2
        text_x = row_x + 18

        # linha 1: tamanho da janela
        row_y = ROW_Y_START
        c.create_image(row_x, row_y, image=row_bg, anchor="nw")
        c.create_text(
            text_x, row_y + 14, text="Tamanho da janela", anchor="nw",
            font=("Consolas", 14, "bold"), fill=LABEL_COLOR,
        )
        size_btn_x = row_x + row_bg.width() - 16 - buy_btn.width()
        caption_max_width = size_btn_x - text_x - 12
        caption_text, caption_size = self._fit_text(
            "Consolas", 11, "normal", "Clique para alternar", caption_max_width
        )
        c.create_text(
            text_x, row_y + 40, text=caption_text, anchor="nw",
            font=("Consolas", caption_size), fill=CAPTION_COLOR,
        )
        size_btn_y = row_y + (row_bg.height() - buy_btn.height()) // 2
        size_btn_item = c.create_image(size_btn_x, size_btn_y, image=buy_btn, anchor="nw")
        self.size_text_item = c.create_text(
            size_btn_x + buy_btn.width() // 2, size_btn_y + buy_btn.height() // 2,
            text="-", font=("Consolas", 12, "bold"), fill=GOLD,
        )
        c.tag_bind(size_btn_item, "<Button-1>", lambda _e: self.bridge.push_command("cycle_size"))
        c.tag_bind(self.size_text_item, "<Button-1>", lambda _e: self.bridge.push_command("cycle_size"))

        # linha 2: fixar sempre no topo (switch)
        row_y += ROW_PITCH
        c.create_image(row_x, row_y, image=row_bg, anchor="nw")
        c.create_text(
            text_x, row_y + 14, text="Fixar sempre no topo", anchor="nw",
            font=("Consolas", 14, "bold"), fill=LABEL_COLOR,
        )
        sw_x = row_x + row_bg.width() - 16 - SWITCH_W
        sw_y = row_y + (row_bg.height() - SWITCH_H) // 2
        pin_caption_max_width = sw_x - text_x - 12
        pin_caption_text, pin_caption_size = self._fit_text(
            "Consolas", 11, "normal", "A janela do jogo fica por cima das outras",
            pin_caption_max_width,
        )
        c.create_text(
            text_x, row_y + 40, text=pin_caption_text, anchor="nw",
            font=("Consolas", pin_caption_size), fill=CAPTION_COLOR,
        )
        self.switch_track = c.create_rectangle(
            sw_x, sw_y, sw_x + SWITCH_W, sw_y + SWITCH_H,
            fill=SWITCH_OFF_COLOR, outline=SWITCH_OUTLINE, width=3,
        )
        knob_r = SWITCH_H // 2 - 3
        self.switch_knob = c.create_oval(
            sw_x + 4, sw_y + 4, sw_x + 4 + knob_r * 2, sw_y + 4 + knob_r * 2,
            fill=SWITCH_KNOB, outline=SWITCH_OUTLINE, width=2,
        )
        self._switch_geom = (sw_x, sw_y, knob_r)
        for item in (self.switch_track, self.switch_knob):
            c.tag_bind(item, "<Button-1>", lambda _e: self.bridge.push_command("toggle_pin"))

        # linha 3: audio (em breve, sem controle nenhum)
        row_y += ROW_PITCH
        c.create_image(row_x, row_y, image=row_bg, anchor="nw")
        c.create_text(
            text_x, row_y + 14, text="Áudio e música", anchor="nw",
            font=("Consolas", 14, "bold"), fill=LABEL_DIM,
        )
        c.create_text(
            text_x, row_y + 40, text="Em breve", anchor="nw",
            font=("Consolas", 11), fill=LABEL_DIM,
        )

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
        if not snapshot:
            return
        c = self.canvas
        c.itemconfig(self.size_text_item, text=snapshot["window_state"])

        pin_on = snapshot["always_on_top"]
        if pin_on != self._pin_on:
            self._pin_on = pin_on
            sw_x, sw_y, knob_r = self._switch_geom
            c.itemconfig(
                self.switch_track, fill=SWITCH_ON_COLOR if pin_on else SWITCH_OFF_COLOR
            )
            knob_x = sw_x + SWITCH_W - 4 - knob_r * 2 if pin_on else sw_x + 4
            c.coords(
                self.switch_knob, knob_x, sw_y + 4, knob_x + knob_r * 2, sw_y + 4 + knob_r * 2
            )
