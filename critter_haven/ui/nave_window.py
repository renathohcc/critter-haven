"""Janela da Nave: um console estelar (Tkinter Canvas, sem moldura do
Windows, mesma técnica do Álbum/Baú/Upgrades) — cada planeta é uma
esfera colorida temática numa tela de visão escura cheia de estrelas,
com status da viagem e um botão "Viajar" (Elyndor, o atual, não tem
botão)."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path

from critter_haven.config.planets import PLANETS
from critter_haven.core.menu_bridge import MenuBridge

ASSETS_UI_DIR = Path(__file__).resolve().parent.parent / "assets" / "ui"

TRANSPARENT_KEY = "#ff00ff"
WINDOW_W, WINDOW_H = 480, 600

GOLD = "#f4d693"
GOLD_DIM = "#8a7a5c"
TITLE_COLOR = "#f4d693"
NAME_COLOR = "#dcdceb"
STATUS_COLOR = "#8c8ca5"
ORB_OUTLINE = "#0a0514"

ROW_Y_START = 76
ROW_PITCH = 124
ORB_RADIUS = 28

# cor tematica da esfera de cada planeta (GDD: tema de cada um)
PLANET_COLORS = {
    "elyndor": "#6ebe6e",
    "calyra": "#d29650",
    "aerthos": "#c8c8d7",
    "glacivar": "#8cbee6",
}


class NaveWindow:
    """Mesma interface duck-typed usada por run_menu_window: window_name,
    sync_visibility(), refresh(snapshot)."""

    window_name = "nave"

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
        self._row_items: dict[str, dict] = {}

        self._load_images()
        self._build_scene()

    @staticmethod
    def _fit_text(family: str, size: int, weight: str, text: str, max_width: int) -> tuple[str, int]:
        """Mesma blindagem usada no menu de Upgrades: encolhe a fonte (ate
        um piso) e, se ainda assim nao coubesse, trunca com reticencias --
        evita que o texto de status invada o botao "Viajar" em telas com
        escala de DPI diferente de 100%."""
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
        for name in ("nave_background", "planet_plaque_bg", "buy_button", "close_x"):
            self._images[name] = tk.PhotoImage(file=str(ASSETS_UI_DIR / f"{name}.png"))

    def _build_scene(self) -> None:
        c = self.canvas
        bg_item = c.create_image(0, 0, image=self._images["nave_background"], anchor="nw")
        c.tag_bind(bg_item, "<ButtonPress-1>", self._start_drag)
        c.tag_bind(bg_item, "<B1-Motion>", self._on_drag)

        c.create_text(
            WINDOW_W // 2, 14, text="NAVE", font=("Consolas", 20, "bold"),
            fill=TITLE_COLOR, anchor="n",
        )

        close_item = c.create_image(WINDOW_W - 52, 12, image=self._images["close_x"], anchor="nw")
        c.tag_bind(close_item, "<Button-1>", lambda _e: self._on_close())

        plaque = self._images["planet_plaque_bg"]
        btn = self._images["buy_button"]
        row_x = (WINDOW_W - plaque.width()) // 2

        row_y = ROW_Y_START
        for planet in PLANETS:
            c.create_image(row_x, row_y, image=plaque, anchor="nw")

            orb_cx = row_x + 46
            orb_cy = row_y + plaque.height() // 2
            c.create_oval(
                orb_cx - ORB_RADIUS, orb_cy - ORB_RADIUS,
                orb_cx + ORB_RADIUS, orb_cy + ORB_RADIUS,
                fill=PLANET_COLORS.get(planet.id, "#999999"), outline=ORB_OUTLINE, width=3,
            )
            c.create_oval(
                orb_cx - 16, orb_cy - 20, orb_cx - 4, orb_cy - 10,
                fill="#ffffff", stipple="gray50", outline="",
            )

            btn_x = row_x + plaque.width() - 20 - btn.width()
            text_x = row_x + 90
            text_max_width = btn_x - text_x - 12 if not planet.active else plaque.width() - 90 - 20

            c.create_text(
                text_x, row_y + 22, text=planet.name, anchor="nw",
                font=("Consolas", 15, "bold"), fill=NAME_COLOR,
            )
            status_text_item = c.create_text(
                text_x, row_y + 50, text="", anchor="nw",
                font=("Consolas", 11), fill=STATUS_COLOR,
            )

            btn_item = None
            btn_text_item = None
            if not planet.active:
                btn_y = row_y + (plaque.height() - btn.height()) // 2
                btn_item = c.create_image(btn_x, btn_y, image=btn, anchor="nw")
                btn_text_item = c.create_text(
                    btn_x + btn.width() // 2, btn_y + btn.height() // 2,
                    text="Viajar", font=("Consolas", 12, "bold"), fill=GOLD,
                )
                pid = planet.id
                c.tag_bind(btn_item, "<Button-1>", lambda _e, p=pid: self._travel(p))
                c.tag_bind(btn_text_item, "<Button-1>", lambda _e, p=pid: self._travel(p))

            self._row_items[planet.id] = {
                "status_text_item": status_text_item,
                "btn_text_item": btn_text_item,
                "text_max_width": text_max_width,
                "can_travel": False,
            }
            row_y += ROW_PITCH

    def _travel(self, planet_id: str) -> None:
        if not self._row_items[planet_id]["can_travel"]:
            self.bridge.play_sfx("denied")
            return
        self.bridge.push_command("travel", planet_id)

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
        planets_info = snapshot.get("planets")
        if not planets_info:
            return
        c = self.canvas
        for planet in PLANETS:
            info = planets_info[planet.id]
            row = self._row_items[planet.id]

            status_text, status_size = self._fit_text(
                "Consolas", 11, "normal", info["status"], row["text_max_width"]
            )
            c.itemconfig(
                row["status_text_item"], text=status_text, font=("Consolas", status_size),
            )

            if not planet.active:
                can_travel = info["can_travel"]
                c.itemconfig(
                    row["btn_text_item"], fill=GOLD if can_travel else GOLD_DIM,
                )
                row["can_travel"] = can_travel
