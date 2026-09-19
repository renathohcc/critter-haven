"""Controle da janela nativa do Windows (always-on-top) sobre a janela SDL.

SDL/Pygame não expõe "always on top" de forma confiável em todas as versões,
então mexemos direto no HWND via win32. Isolado aqui para que o resto do jogo
nunca precise saber que estamos no Windows.
"""

from __future__ import annotations

import sys

import pygame

_SUPPORTED = sys.platform == "win32"

if _SUPPORTED:
    import win32con
    import win32gui


def get_hwnd() -> int | None:
    if not _SUPPORTED:
        return None
    info = pygame.display.get_wm_info()
    return info.get("window")


def set_always_on_top(enabled: bool) -> bool:
    """Retorna True se a chamada foi aplicada (plataforma suportada)."""
    hwnd = get_hwnd()
    if hwnd is None:
        return False
    flag = win32con.HWND_TOPMOST if enabled else win32con.HWND_NOTOPMOST
    win32gui.SetWindowPos(
        hwnd,
        flag,
        0,
        0,
        0,
        0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
    )
    return True


def is_supported() -> bool:
    return _SUPPORTED


def is_foreground() -> bool | None:
    """Se a janela do jogo é a janela ativa do Windows no momento.

    Mais confiável que os eventos WINDOWFOCUSGAINED/LOST do SDL, que
    ficam inconsistentes quando a janela está com always-on-top ativo
    (o próprio Pygame às vezes reporta foco mesmo com outra janela em
    primeiro plano). Retorna None se não suportado (fora do Windows).
    """
    if not _SUPPORTED:
        return None
    hwnd = get_hwnd()
    if hwnd is None:
        return None
    return win32gui.GetForegroundWindow() == hwnd
