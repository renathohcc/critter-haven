"""Janela de Upgrades: um pergaminho enrolado (Tkinter Canvas, sem
moldura do Windows, mesma técnica do Álbum/Baú) listando cada upgrade
com ícone temático, nível atual e um botão de compra que apaga quando
falta ouro ou o upgrade já está no nível máximo.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path

from critter_haven.config.upgrades import UPGRADES
from critter_haven.core.menu_bridge import MenuBridge

ASSETS_UI_DIR = Path(__file__).resolve().parent.parent / "assets" / "ui"

TRANSPARENT_KEY = "#ff00ff"
WINDOW_W, WINDOW_H = 480, 680

GOLD = "#f4d693"
GOLD_DIM = "#8a7a5c"
TITLE_COLOR = "#f4d693"
TEXT_DARK = "#3c2819"
TEXT_MUTED = "#78643d"

ROW_Y_START = 96
ROW_PITCH = 104

# cada upgrade usa um icone tematico proprio, reaproveitando os que ja
# existem na HUD quando fazem sentido (moeda/pata/bau) e 2 novos so
# pra Upgrades (ampulheta, lua)
UPGRADE_ICONS = {
    "gold_production": "icon_coin",
    "spawn_speed": "icon_hourglass",
    "habitat_capacity": "icon_paw",
    "chest_capacity": "icon_chest_small",
    "offline_progress": "icon_moon",
}


class UpgradesWindow:
    """Mesma interface duck-typed usada por run_menu_window: window_name,
    sync_visibility(), refresh(snapshot)."""

    window_name = "upgrades"

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
        """Encolhe a fonte (ate um piso) e, se ainda assim nao coubesse,
        trunca com reticencias -- garante que o texto nunca invada o
        botao ao lado, seja qual for a fonte/DPI renderizando de
        verdade (o mesmo texto pode ficar bem mais largo em telas com
        escala >100%, foi isso que causou a sobreposicao relatada)."""
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
        for name in (
            "scroll_background", "item_plaque_bg", "buy_button", "close_x",
            *UPGRADE_ICONS.values(),
        ):
            self._images[name] = tk.PhotoImage(file=str(ASSETS_UI_DIR / f"{name}.png"))

    def _build_scene(self) -> None:
        c = self.canvas
        bg_item = c.create_image(0, 0, image=self._images["scroll_background"], anchor="nw")
        c.tag_bind(bg_item, "<ButtonPress-1>", self._start_drag)
        c.tag_bind(bg_item, "<B1-Motion>", self._on_drag)

        c.create_text(
            WINDOW_W // 2, 16, text="UPGRADES", font=("Consolas", 20, "bold"),
            fill=TITLE_COLOR, anchor="n",
        )

        close_item = c.create_image(WINDOW_W - 52, 12, image=self._images["close_x"], anchor="nw")
        c.tag_bind(close_item, "<Button-1>", lambda _e: self._on_close())

        plaque = self._images["item_plaque_bg"]
        sell_btn = self._images["buy_button"]
        row_x = (WINDOW_W - plaque.width()) // 2
        icon_box = 36

        row_y = ROW_Y_START
        for upgrade in UPGRADES:
            c.create_image(row_x, row_y, image=plaque, anchor="nw")

            icon = self._images[UPGRADE_ICONS[upgrade.id]]
            icon_x = row_x + 12 + (icon_box - icon.width()) // 2
            icon_y = row_y + (plaque.height() - icon.height()) // 2
            c.create_image(icon_x, icon_y, image=icon, anchor="nw")

            text_x = row_x + 12 + icon_box + 12
            btn_x = row_x + plaque.width() - 16 - sell_btn.width()
            text_max_width = btn_x - text_x - 12

            name_text, name_size = self._fit_text(
                "Consolas", 14, "bold", upgrade.name, text_max_width
            )
            c.create_text(
                text_x, row_y + 16, text=name_text, anchor="nw",
                font=("Consolas", name_size, "bold"), fill=TEXT_DARK,
            )
            level_text_item = c.create_text(
                text_x, row_y + 42, text="", anchor="nw",
                font=("Consolas", 11), fill=TEXT_MUTED,
            )

            btn_y = row_y + (plaque.height() - sell_btn.height()) // 2
            btn_item = c.create_image(btn_x, btn_y, image=sell_btn, anchor="nw")
            btn_text_item = c.create_text(
                btn_x + sell_btn.width() // 2, btn_y + sell_btn.height() // 2,
                text="Comprar", font=("Consolas", 12, "bold"), fill=GOLD,
            )

            uid = upgrade.id
            c.tag_bind(btn_item, "<Button-1>", lambda _e, u=uid: self._buy(u))
            c.tag_bind(btn_text_item, "<Button-1>", lambda _e, u=uid: self._buy(u))

            self._row_items[uid] = {
                "level_text_item": level_text_item,
                "btn_text_item": btn_text_item,
                "can_buy": False,
                "text_max_width": text_max_width,
            }
            row_y += ROW_PITCH

    def _buy(self, upgrade_id: str) -> None:
        if not self._row_items[upgrade_id]["can_buy"]:
            self.bridge.play_sfx("denied")
            return
        self.bridge.push_command("buy_upgrade", upgrade_id)

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
        upgrades_info = snapshot.get("upgrades")
        if not upgrades_info:
            return
        c = self.canvas
        for upgrade in UPGRADES:
            info = upgrades_info[upgrade.id]
            row = self._row_items[upgrade.id]
            if info["cost"] is None:
                raw_text = f"Nível {info['level']}/{upgrade.max_level}  ·  MÁXIMO"
                c.itemconfig(row["btn_text_item"], text="MAX", fill=GOLD_DIM)
                row["can_buy"] = False
            else:
                raw_text = f"Nível {info['level']}/{upgrade.max_level}  ·  {info['cost']:.0f} ouro"
                can_afford = info["can_afford"]
                c.itemconfig(
                    row["btn_text_item"], text="Comprar",
                    fill=GOLD if can_afford else GOLD_DIM,
                )
                row["can_buy"] = can_afford

            level_text, level_size = self._fit_text(
                "Consolas", 11, "normal", raw_text, row["text_max_width"]
            )
            c.itemconfig(
                row["level_text_item"], text=level_text, font=("Consolas", level_size),
            )
