"""Canal thread-safe entre o loop do Pygame (thread principal) e a janela
de menu em Tkinter (thread secundária). Nenhuma das duas threads mexe
diretamente no estado da outra — tudo passa por aqui.

- `publish`/`read_snapshot`: dados de exibição, produzidos pelo Pygame e
  lidos periodicamente pelo Tkinter (padrão "último valor vence").
- `push_command`/`drain_commands`: cliques no menu viram comandos que o
  loop do Pygame aplica ao estado real do jogo, evitando duas threads
  mutando o mesmo objeto ao mesmo tempo.
- `push_to_menu`/`drain_to_menu_commands`: mão contrária — a barra
  overlay pede pro Tkinter fazer algo (ex: "abrir já na aba Álbum").
- `visible`/`stop_event`: flags simples que o Tkinter consulta a cada
  poll para saber se deve aparecer/esconder ou encerrar.
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
    _visible_lock: threading.Lock = field(default_factory=threading.Lock)
    _visible: bool = False

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

    def set_visible(self, visible: bool) -> None:
        with self._visible_lock:
            self._visible = visible

    def toggle_visible(self) -> None:
        with self._visible_lock:
            self._visible = not self._visible

    def is_visible(self) -> bool:
        with self._visible_lock:
            return self._visible
