"""Regras de energia e raridade de spawn (GDD seção 8)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RarityConfig:
    name: str
    weight: float
    gold_multiplier: float


COMMON = RarityConfig(name="common", weight=70, gold_multiplier=1.0)
RARE = RarityConfig(name="rare", weight=25, gold_multiplier=2.5)
SPECIAL = RarityConfig(name="special", weight=5, gold_multiplier=6.0)

RARITIES = (COMMON, RARE, SPECIAL)
RARITY_BY_NAME = {r.name: r for r in RARITIES}

ENERGY_MAX = 60.0
ENERGY_PER_SECOND = 1.0  # tempo de spawn = ENERGY_MAX / ENERGY_PER_SECOND (~60s base)

# Capacidade inicial do habitat. Upgrades de capacidade (Fase 4) devem
# aumentar Habitat.max_creatures em runtime, não este valor base.
BASE_MAX_CREATURES = 6
