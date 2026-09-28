"""Janelas de menu separadas (Tkinter, thread própria): Baú, Upgrades,
Nave, Fusão e Álbum são janelas Tkinter independentes, cada uma aberta e
fechada isoladamente pelo respectivo ícone na HUD. Roda numa thread
dedicada; toda comunicação com o jogo (Pygame, thread principal) passa
pelo MenuBridge — nunca lemos/escrevemos o estado do jogo diretamente
aqui.

O Álbum (`critter_haven.ui.album_window.AlbumWindow`) é o único que
foge do padrão ttk genérico — é um livro em pixel art desenhado à mão
num Canvas, sem moldura do Windows.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from critter_haven.config.planets import PLANETS
from critter_haven.config.upgrades import UPGRADES
from critter_haven.core.menu_bridge import MenuBridge
from critter_haven.ui.album_window import AlbumWindow

POLL_INTERVAL_MS = 200

RARITY_LABEL = {"common": "Comum", "rare": "Rara", "special": "Especial"}


class MenuToplevel:
    """Base comum para uma janela de menu independente: começa escondida,
    aparece/some conforme `bridge.is_window_visible(window_name)` e nunca
    é destruída, só escondida (fechar = esconder, não sair do jogo)."""

    window_name = ""
    title = ""
    geometry = "420x480"
    minsize = (360, 360)

    def __init__(self, root: tk.Tk, bridge: MenuBridge) -> None:
        self.bridge = bridge
        self.top = tk.Toplevel(root)
        self.top.title(self.title)
        self.top.geometry(self.geometry)
        self.top.minsize(*self.minsize)
        self.top.protocol("WM_DELETE_WINDOW", self._on_close)
        self.top.withdraw()
        self._build_widgets(self.top)

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

    def _build_widgets(self, parent: tk.Toplevel) -> None:
        raise NotImplementedError

    def refresh(self, snapshot: dict) -> None:
        raise NotImplementedError


class BauWindow(MenuToplevel):
    window_name = "bau"
    title = "Critter Haven — Baú"
    geometry = "360x360"
    minsize = (320, 300)

    def _build_widgets(self, parent: tk.Toplevel) -> None:
        stats = ttk.LabelFrame(parent, text="Habitat")
        stats.pack(fill="x", padx=8, pady=6)
        self.gold_label = ttk.Label(stats, text="Ouro: -", anchor="w")
        self.gold_label.pack(fill="x", padx=6, pady=2)
        self.creatures_label = ttk.Label(stats, text="Criaturas: -", anchor="w")
        self.creatures_label.pack(fill="x", padx=6, pady=2)
        self.chest_label = ttk.Label(stats, text="Baú: -", anchor="w")
        self.chest_label.pack(fill="x", padx=6, pady=2)

        controls = ttk.LabelFrame(parent, text="Janela")
        controls.pack(fill="x", padx=8, pady=6)
        self.size_button = ttk.Button(
            controls, text="Tamanho", command=lambda: self.bridge.push_command("cycle_size")
        )
        self.size_button.pack(side="left", padx=6, pady=6)
        self.pin_button = ttk.Button(
            controls, text="Fixar", command=lambda: self.bridge.push_command("toggle_pin")
        )
        self.pin_button.pack(side="left", padx=6, pady=6)

    def refresh(self, snapshot: dict) -> None:
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


class UpgradesWindow(MenuToplevel):
    window_name = "upgrades"
    title = "Critter Haven — Upgrades"
    geometry = "420x420"
    minsize = (360, 320)

    def _build_widgets(self, parent: tk.Toplevel) -> None:
        upgrades_frame = ttk.LabelFrame(parent, text="Upgrades")
        upgrades_frame.pack(fill="both", expand=True, padx=8, pady=6)
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

    def refresh(self, snapshot: dict) -> None:
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


class NaveWindow(MenuToplevel):
    window_name = "nave"
    title = "Critter Haven — Nave"
    geometry = "440x420"
    minsize = (360, 320)

    def _build_widgets(self, parent: tk.Toplevel) -> None:
        ship_frame = ttk.LabelFrame(parent, text="Destinos")
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
                info, text="", anchor="w", justify="left", wraplength=300
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

    def refresh(self, snapshot: dict) -> None:
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


class FusionWindow(MenuToplevel):
    window_name = "fusion"
    title = "Critter Haven — Fusão"
    geometry = "380x460"
    minsize = (340, 380)

    def _build_widgets(self, parent: tk.Toplevel) -> None:
        ttk.Label(
            parent,
            text="Selecione 2 criaturas para fundir e sortear uma nova.",
            anchor="w",
            justify="left",
            wraplength=340,
        ).pack(fill="x", padx=8, pady=(8, 4))

        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True, padx=8, pady=4)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        self.listbox = tk.Listbox(
            list_frame,
            selectmode=tk.MULTIPLE,
            exportselection=False,
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=self.listbox.yview)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", self._on_selection_change)

        self.fuse_button = ttk.Button(
            parent, text="Fundir (consome as 2)", command=self._on_fuse_clicked
        )
        self.fuse_button.pack(fill="x", padx=8, pady=6)
        self.fuse_button.state(["disabled"])

        self.result_label = ttk.Label(
            parent, text="", anchor="w", justify="left", wraplength=340, foreground="#2a6b2a"
        )
        self.result_label.pack(fill="x", padx=8, pady=(0, 8))

        self._creature_ids: list[int] = []
        self._last_snapshot_ids: list[int] | None = None

    def _on_selection_change(self, _event=None) -> None:
        selected = self.listbox.curselection()
        if len(selected) > 2:
            # só deixa marcar 2 -- desmarca a mais antiga selecionada em vez
            # de travar a UI, assim o jogador so precisa clicar na proxima.
            self.listbox.selection_clear(selected[0])
            selected = self.listbox.curselection()
        if len(selected) == 2:
            self.fuse_button.state(["!disabled"])
        else:
            self.fuse_button.state(["disabled"])

    def _on_fuse_clicked(self) -> None:
        selected = self.listbox.curselection()
        if len(selected) != 2:
            return
        id_a = self._creature_ids[selected[0]]
        id_b = self._creature_ids[selected[1]]
        self.bridge.push_command("fuse", (id_a, id_b))
        self.listbox.selection_clear(0, tk.END)
        self.fuse_button.state(["disabled"])

    def refresh(self, snapshot: dict) -> None:
        creatures = snapshot.get("creatures", [])
        ids = [entry["id"] for entry in creatures]
        # só reconstrói a lista quando o conjunto de criaturas realmente
        # mudou -- senão a cada poll (200ms) a selecao do jogador seria
        # apagada antes de ele conseguir clicar em "Fundir".
        if ids != self._last_snapshot_ids:
            self._last_snapshot_ids = ids
            self._creature_ids = ids
            self.listbox.delete(0, tk.END)
            for entry in creatures:
                rarity = RARITY_LABEL.get(entry["rarity"], entry["rarity"])
                self.listbox.insert(tk.END, f"{entry['name']} ({rarity})")
            self.fuse_button.state(["disabled"])

        result = snapshot.get("last_fusion_result")
        if result:
            self.result_label.config(text=result)


WINDOW_CLASSES = (BauWindow, UpgradesWindow, NaveWindow, AlbumWindow, FusionWindow)


def run_menu_window(bridge: MenuBridge) -> None:
    root = tk.Tk()
    root.withdraw()

    windows = {cls.window_name: cls(root, bridge) for cls in WINDOW_CLASSES}

    def poll() -> None:
        if bridge.stop_event.is_set():
            root.destroy()
            return

        for name, payload in bridge.drain_to_menu_commands():
            if name == "show_window":
                bridge.show_window(payload)

        for menu_window in windows.values():
            menu_window.sync_visibility()

        if any(bridge.is_window_visible(name) for name in windows):
            snapshot = bridge.read_snapshot()
            if snapshot:
                for name, menu_window in windows.items():
                    if bridge.is_window_visible(name):
                        menu_window.refresh(snapshot)

        root.after(POLL_INTERVAL_MS, poll)

    poll()
    root.mainloop()
