"""Regras de energia e raridade de spawn (GDD seção 8)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RarityConfig:
    name: str
    weight: float
    gold_multiplier: float


COMMON = RarityConfig(name="common", weight=85, gold_multiplier=1.0)
RARE = RarityConfig(name="rare", weight=13, gold_multiplier=2.5)
SPECIAL = RarityConfig(name="special", weight=2, gold_multiplier=6.0)

RARITIES = (COMMON, RARE, SPECIAL)
RARITY_BY_NAME = {r.name: r for r in RARITIES}

# Pesos de raridade ao sortear a nova criatura na Fusão (Fase 8 revisão
# 2): o jogador consome 2 criaturas quaisquer do habitat (de espécies
# iguais ou diferentes) e a raridade sorteada depende da COMBINAÇÃO das
# raridades das duas usadas — quanto mais raras as duas, maior a chance
# de o resultado também ser raro/especial. Chave: tupla das duas
# raridades em ordem alfabética (ver `fusion_key` em spawn_system.py).
FUSION_RARITY_WEIGHTS: dict[tuple[str, str], dict[str, float]] = {
    ("common", "common"): {"common": 70, "rare": 28, "special": 2},
    ("common", "rare"): {"common": 45, "rare": 47, "special": 8},
    ("common", "special"): {"common": 30, "rare": 55, "special": 15},
    ("rare", "rare"): {"common": 25, "rare": 65, "special": 10},
    ("rare", "special"): {"common": 15, "rare": 65, "special": 20},
    ("special", "special"): {"common": 10, "rare": 60, "special": 30},
}

ENERGY_MAX = 60.0
ENERGY_PER_SECOND = 1.0  # tempo de spawn = ENERGY_MAX / ENERGY_PER_SECOND (~60s base)

# Capacidade inicial do habitat. Upgrades de capacidade (Fase 4) devem
# aumentar Habitat.max_creatures em runtime, não este valor base.
BASE_MAX_CREATURES = 6
