import random

from critter_haven.data.species import load_planet
from critter_haven.systems.spawn_system import roll_rarity, roll_species


def test_roll_rarity_distribution_matches_weights():
    rng = random.Random(42)
    counts = {"common": 0, "rare": 0, "special": 0}
    for _ in range(20000):
        counts[roll_rarity(rng)] += 1
    total = sum(counts.values())
    assert 0.65 < counts["common"] / total < 0.75
    assert 0.20 < counts["rare"] / total < 0.30
    assert 0.02 < counts["special"] / total < 0.08


def test_roll_species_returns_species_of_pool():
    pool = load_planet("elyndor")
    rng = random.Random(1)
    species = roll_species(pool, rng)
    assert species in pool
