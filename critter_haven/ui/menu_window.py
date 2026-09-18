"""Janela de menu separada (Tkinter, thread própria) com o painel
completo do habitat: stats, upgrades e nave. Roda numa thread dedicada;
toda comunicação com o jogo (Pygame, thread principal) passa pelo
MenuBridge — nunca lemos/escrevemos o estado do jogo diretamente aqui.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from critter_haven.config.upgrades import UPGRADES
from critter_haven.config.planets import PLANETS
from critter_haven.core.menu_bridge import MenuBridge

POLL_INTERVAL_MS = 200


class MenuWindow:
    def __init__(self, root: tk.Tk, bridge: MenuBridge) -> None:
        self.root = root
        self.bridge = bridge
        self.root.title("Critter Haven — Menu")
        self.root.geometry("560x640")
        self.root.minsize(480, 520)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_widgets()
        self._poll()

    def _on_close(self) -> None:
        self.bridge.set_visible(False)
        self.root.withdraw()

    def _build_widgets(self) -> None:
        stats = ttk.LabelFrame(self.root, text="Habitat")
        stats.pack(fill="x", padx=8, pady=6)
        self.gold_label = ttk.Label(stats, text="Ouro: -", anchor="w")
        self.gold_label.pack(fill="x", padx=6, pady=2)
        self.creatures_label = ttk.Label(stats, text="Criaturas: -", anchor="w")
        self.creatures_label.pack(fill="x", padx=6, pady=2)
        self.chest_label = ttk.Label(stats, text="Baú: -", anchor="w")
        self.chest_label.pack(fill="x", padx=6, pady=2)

        controls = ttk.LabelFrame(self.root, text="Janela")
        controls.pack(fill="x", padx=8, pady=6)
        self.size_button = ttk.Button(
            controls, text="Tamanho", command=lambda: self.bridge.push_command("cycle_size")
        )
        self.size_button.pack(side="left", padx=6, pady=6)
        self.pin_button = ttk.Button(
            controls, text="Fixar", command=lambda: self.bridge.push_command("toggle_pin")
        )
        self.pin_button.pack(side="left", padx=6, pady=6)
        self.album_button = ttk.Button(controls, text="Álbum (em breve)", state="disabled")
        self.album_button.pack(side="left", padx=6, pady=6)

        upgrades_frame = ttk.LabelFrame(self.root, text="Upgrades")
        upgrades_frame.pack(fill="x", padx=8, pady=6)
        self.upgrade_rows: dict[str, dict[str, tk.Widget]] = {}
        for upgrade in UPGRADES:
            row = ttk.Frame(upgrades_frame)
            row.pack(fill="x", padx=4, pady=3)
            label = ttk.Label(row, text=upgrade.name, anchor="w", justify="left")
            label.pack(side="left", fill="x", expand=True)
            button = ttk.Button(
                row,
                text="...",
                width=12,
                command=lambda uid=upgrade.id: self.bridge.push_command("buy_upgrade", uid),
            )
            button.pack(side="right")
            self.upgrade_rows[upgrade.id] = {"label": label, "button": button}

        ship_frame = ttk.LabelFrame(self.root, text="Nave — Destinos")
        ship_frame.pack(fill="both", expand=True, padx=8, pady=6)
        self.ship_rows: dict[str, dict[str, tk.Widget]] = {}
        for planet in PLANETS:
            row = ttk.Frame(ship_frame)
            row.pack(fill="x", padx=4, pady=4)
            info = ttk.Frame(row)
            info.pack(side="left", fill="x", expand=True)
            name_label = ttk.Label(
                info, text=planet.name, anchor="w", justify="left", font=("TkDefaultFont", 10, "bold")
            )
            name_label.pack(fill="x")
            status_label = ttk.Label(
                info, text="", anchor="w", justify="left", wraplength=340
            )
            status_label.pack(fill="x")
            button = ttk.Button(
                row,
                text="Viajar",
                width=10,
                command=lambda pid=planet.id: self.bridge.push_command("travel", pid),
            )
            button.pack(side="right", anchor="n")
            if planet.active:
                button.state(["disabled"])
            self.ship_rows[planet.id] = {
                "name_label": name_label,
                "status_label": status_label,
                "button": button,
            }

    def _poll(self) -> None:
        if self.bridge.stop_event.is_set():
            self.root.destroy()
            return

        should_show = self.bridge.is_visible()
        is_mapped = bool(self.root.winfo_ismapped())
        if should_show and not is_mapped:
            self.root.deiconify()
        elif not should_show and is_mapped:
            self.root.withdraw()

        if should_show:
            self._refresh(self.bridge.read_snapshot())

        self.root.after(POLL_INTERVAL_MS, self._poll)

    def _refresh(self, snapshot: dict) -> None:
        if not snapshot:
            return
        self.gold_label.config(
            text=f"Ouro: {snapshot['gold']:.0f}   (+{snapshot['gold_per_second']:.0f}/s)"
        )
        self.creatures_label.config(
            text=f"Criaturas: {snapshot['creature_count']}/{snapshot['max_creatures']}"
        )
        self.chest_label.config(
            text=f"Baú: {snapshot['chest_count']}/{snapshot['chest_capacity']} itens"
        )
        self.size_button.config(text=f"Tamanho: {snapshot['window_state']}")
        self.pin_button.config(
            text=f"Fixar: {'ON' if snapshot['always_on_top'] else 'OFF'}"
        )

        for upgrade in UPGRADES:
            info = snapshot["upgrades"][upgrade.id]
            widgets = self.upgrade_rows[upgrade.id]
            widgets["label"].config(text=f"{upgrade.name} (nv {info['level']}/{upgrade.max_level})")
            if info["cost"] is None:
                widgets["button"].config(text="MAX")
                widgets["button"].state(["disabled"])
            else:
                widgets["button"].config(text=f"{info['cost']:.0f} ouro")
                if info["can_afford"]:
                    widgets["button"].state(["!disabled"])
                else:
                    widgets["button"].state(["disabled"])

        for planet in PLANETS:
            info = snapshot["planets"][planet.id]
            widgets = self.ship_rows[planet.id]
            widgets["status_label"].config(text=info["status"])
            if planet.active:
                widgets["button"].state(["disabled"])
            elif info["can_travel"]:
                widgets["button"].state(["!disabled"])
            else:
                widgets["button"].state(["disabled"])


def run_menu_window(bridge: MenuBridge) -> None:
    root = tk.Tk()
    root.withdraw()
    MenuWindow(root, bridge)
    root.mainloop()
