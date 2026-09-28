"""Sorteio de raridade e espécie no spawn (GDD seção 8)."""

from __future__ import annotations

import random

from critter_haven.config.spawn import FUSION_RARITY_WEIGHTS, RARITIES
from critter_haven.data.species import Species, by_rarity


def roll_rarity(rng: random.Random | None = None) -> str:
    rng = rng or random
    weights = [r.weight for r in RARITIES]
    return rng.choices([r.name for r in RARITIES], weights=weights, k=1)[0]


def roll_species(pool: list[Species], rng: random.Random | None = None) -> Species:
    rng = rng or random
    rarity = roll_rarity(rng)
    candidates = by_rarity(pool, rarity)
    if not candidates:
        # fallback defensivo: se não há espécie dessa raridade no planeta,
        # sorteia entre todas as disponíveis em vez de travar o spawn.
        candidates = pool
    return rng.choice(candidates)


def fusion_key(rarity_a: str, rarity_b: str) -> tuple[str, str]:
    return tuple(sorted((rarity_a, rarity_b)))


def roll_rarity_for_fusion(
    rarity_a: str, rarity_b: str, rng: random.Random | None = None
) -> str:
    """Sorteia a raridade da nova criatura ao fundir duas criaturas
    quaisquer (mecânica de Fusão) — a tabela de pesos depende da
    combinação de raridades das duas usadas, não das espécies em si:
    fundir duas criaturas raras/especiais aumenta bastante a chance do
    resultado também ser raro/especial."""
    rng = rng or random
    table = FUSION_RARITY_WEIGHTS.get(fusion_key(rarity_a, rarity_b))
    if table is None:
        return roll_rarity(rng)
    names = list(table.keys())
    weights = list(table.values())
    return rng.choices(names, weights=weights, k=1)[0]


def roll_species_for_fusion(
    pool: list[Species], rarity_a: str, rarity_b: str, rng: random.Random | None = None
) -> Species:
    rng = rng or random
    rarity = roll_rarity_for_fusion(rarity_a, rarity_b, rng)
    candidates = by_rarity(pool, rarity)
    if not candidates:
        candidates = pool
    return rng.choice(candidates)
