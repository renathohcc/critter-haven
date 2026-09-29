"""Janelas de menu separadas (Tkinter, thread própria): Baú, Upgrades,
Nave, Fusão, Álbum e Configurações são janelas Tkinter independentes,
cada uma aberta e fechada isoladamente pelo respectivo ícone na HUD.
Roda numa thread dedicada; toda comunicação com o jogo (Pygame, thread
principal) passa pelo MenuBridge — nunca lemos/escrevemos o estado do
jogo diretamente aqui.

Todas as janelas (`critter_haven.ui.album_window.AlbumWindow`,
`critter_haven.ui.chest_window.ChestWindow`,
`critter_haven.ui.upgrades_window.UpgradesWindow`,
`critter_haven.ui.nave_window.NaveWindow`,
`critter_haven.ui.fusion_window.FusionWindow`,
`critter_haven.ui.settings_window.SettingsWindow`) são pixel art
desenhada à mão num Canvas, sem moldura do Windows -- nenhuma usa mais
o ttk genérico.
"""

from __future__ import annotations

import tkinter as tk

from critter_haven.core.menu_bridge import MenuBridge
from critter_haven.ui.album_window import AlbumWindow
from critter_haven.ui.chest_window import ChestWindow
from critter_haven.ui.fusion_window import FusionWindow
from critter_haven.ui.nave_window import NaveWindow
from critter_haven.ui.settings_window import SettingsWindow
from critter_haven.ui.upgrades_window import UpgradesWindow

POLL_INTERVAL_MS = 200



WINDOW_CLASSES = (ChestWindow, UpgradesWindow, NaveWindow, AlbumWindow, FusionWindow, SettingsWindow)


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
