"""Referência de altura/conteúdo dos 3 estados de UI (GDD seção 10)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowState:
    name: str
    min_height: int
    reference_height: int


COMPACT = WindowState(name="compact", min_height=90, reference_height=120)
MEDIUM = WindowState(name="medium", min_height=121, reference_height=220)
EXPANDED = WindowState(name="expanded", min_height=221, reference_height=400)

STATES = (COMPACT, MEDIUM, EXPANDED)

DEFAULT_WIDTH = 900
DEFAULT_HEIGHT = MEDIUM.reference_height


def state_for_height(height: int) -> WindowState:
    if height <= COMPACT.min_height + 30:
        return COMPACT
    if height < EXPANDED.min_height:
        return MEDIUM
    return EXPANDED
