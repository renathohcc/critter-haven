"""Carrega os dados de espécies de criaturas a partir de creatures.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources


@dataclass(frozen=True)
class Species:
    id: str
    name: str
    planet: str
    rarity: str
    base_gold_per_second: float
    item_name: str
    description: str


def load_all() -> dict[str, list[Species]]:
    raw = resources.files("critter_haven.data").joinpath("creatures.json").read_text(
        encoding="utf-8"
    )
    data = json.loads(raw)
    return {
        planet: [Species(**entry) for entry in entries]
        for planet, entries in data.items()
    }


def load_planet(planet: str) -> list[Species]:
    return load_all()[planet]


def load_planet_safe(planet: str) -> list[Species]:
    """Como load_planet, mas retorna lista vazia se o planeta ainda não
    tem criaturas definidas (Calyra/Aerthos/Glacivar são pós-demo)."""
    return load_all().get(planet, [])


def by_rarity(species: list[Species], rarity: str) -> list[Species]:
    return [s for s in species if s.rarity == rarity]
