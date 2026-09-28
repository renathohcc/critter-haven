"""Canal thread-safe entre o loop do Pygame (thread principal) e a janela
de menu em Tkinter (thread secundária). Nenhuma das duas threads mexe
diretamente no estado da outra — tudo passa por aqui.

- `publish`/`read_snapshot`: dados de exibição, produzidos pelo Pygame e
  lidos periodicamente pelo Tkinter (padrão "último valor vence").
- `push_command`/`drain_commands`: cliques no menu viram comandos que o
  loop do Pygame aplica ao estado real do jogo, evitando duas threads
  mutando o mesmo objeto ao mesmo tempo.
- `push_to_menu`/`drain_to_menu_commands`: mão contrária — a barra
  overlay pede pro Tkinter fazer algo (ex: "abrir a janela do Álbum").
- `show_window`/`hide_window`/`is_window_visible`: cada menu (Baú,
  Upgrades, Nave, Álbum) é uma janela Tkinter própria e independente;
  este dicionário guarda o estado de visibilidade de cada uma.
- `stop_event`: flag simples que o Tkinter consulta a cada poll para
  saber se deve encerrar.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MenuBridge:
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _snapshot: dict[str, Any] = field(default_factory=dict)
    commands: "queue.Queue[tuple[str, Any]]" = field(default_factory=queue.Queue)
    to_menu_commands: "queue.Queue[tuple[str, Any]]" = field(default_factory=queue.Queue)
    stop_event: threading.Event = field(default_factory=threading.Event)
    _window_visible_lock: threading.Lock = field(default_factory=threading.Lock)
    _window_visible: dict[str, bool] = field(default_factory=dict)

    def publish(self, snapshot: dict[str, Any]) -> None:
        with self._lock:
            self._snapshot = snapshot

    def read_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._snapshot)

    def push_command(self, name: str, payload: Any = None) -> None:
        self.commands.put((name, payload))

    def drain_commands(self) -> list[tuple[str, Any]]:
        drained = []
        while True:
            try:
                drained.append(self.commands.get_nowait())
            except queue.Empty:
                break
        return drained

    def push_to_menu(self, name: str, payload: Any = None) -> None:
        self.to_menu_commands.put((name, payload))

    def drain_to_menu_commands(self) -> list[tuple[str, Any]]:
        drained = []
        while True:
            try:
                drained.append(self.to_menu_commands.get_nowait())
            except queue.Empty:
                break
        return drained

    def show_window(self, name: str) -> None:
        with self._window_visible_lock:
            self._window_visible[name] = True

    def hide_window(self, name: str) -> None:
        with self._window_visible_lock:
            self._window_visible[name] = False

    def is_window_visible(self, name: str) -> bool:
        with self._window_visible_lock:
            return self._window_visible.get(name, False)
