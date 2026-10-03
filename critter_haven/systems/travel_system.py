"""Verificação de liberação de planetas (Fase 11): um destino abre quando a
defesa do planeta anterior da cadeia foi vencida."""

from __future__ import annotations

from collections.abc import Collection

from critter_haven.config.planets import PlanetDestination


def can_travel(destination: PlanetDestination, cleared_defenses: Collection[str]) -> bool:
    if destination.active:
        return True
    return destination.unlock_after is not None and destination.unlock_after in cleared_defenses


def travel(destination: PlanetDestination, cleared_defenses: Collection[str]) -> bool:
    return can_travel(destination, cleared_defenses)
