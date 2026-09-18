"""Sorteio de raridade e espécie no spawn (GDD seção 8)."""

from __future__ import annotations

import random

from critter_haven.config.spawn import RARITIES
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
