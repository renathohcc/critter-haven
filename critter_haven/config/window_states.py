"""Os 3 tamanhos fixos de janela (GDD seção 10). A janela não é
redimensionável livremente — o jogador alterna entre estes presets."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowState:
    name: str
    width: int
    height: int


COMPACT = WindowState(name="compact", width=900, height=120)
MEDIUM = WindowState(name="medium", width=900, height=220)
EXPANDED = WindowState(name="expanded", width=900, height=420)

STATES = (COMPACT, MEDIUM, EXPANDED)

DEFAULT_STATE = MEDIUM
DEFAULT_WIDTH = DEFAULT_STATE.width
DEFAULT_HEIGHT = DEFAULT_STATE.height


def next_state(current: WindowState) -> WindowState:
    index = STATES.index(current)
    return STATES[(index + 1) % len(STATES)]
