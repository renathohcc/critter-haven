import random

from critter_haven.data.species import load_planet
from critter_haven.entities.creature import Creature
from critter_haven.entities.habitat import Habitat
from critter_haven.systems.spawn_system import fusion_key, roll_rarity_for_fusion


def get_species(species_id: str):
    return next(s for s in load_planet("elyndor") if s.id == species_id)


def make_habitat() -> Habitat:
    return Habitat(planet="elyndor", species_pool=load_planet("elyndor"))


def add_creature(habitat: Habitat, species_id: str, x: float = 0.0) -> Creature:
    creature = Creature(species=get_species(species_id), x=x, y=0)
    habitat.creatures.append(creature)
    return creature


def test_can_fuse_requires_two_distinct_living_creatures():
    habitat = make_habitat()
    a = add_creature(habitat, "mossnib", 0)
    b = add_creature(habitat, "pebblit", 10)

    assert habitat.can_fuse(id(a), id(b)) is True
    assert habitat.can_fuse(id(a), id(a)) is False
    assert habitat.can_fuse(id(a), 999999) is False


def test_fuse_creatures_consumes_both_regardless_of_species():
    habitat = make_habitat()
    a = add_creature(habitat, "mossnib", 0)
    b = add_creature(habitat, "breezel", 10)

    result = habitat.fuse_creatures(id(a), id(b))

    assert result is not None
    # removeu as 2 usadas na fusao + adicionou 1 sorteada = 1
    assert len(habitat.creatures) == 1
    assert a not in habitat.creatures
    assert b not in habitat.creatures


def test_fuse_creatures_fails_with_invalid_ids():
    habitat = make_habitat()
    a = add_creature(habitat, "mossnib", 0)

    assert habitat.fuse_creatures(id(a), 999999) is None
    assert len(habitat.creatures) == 1


def test_fuse_can_work_even_when_habitat_is_full():
    habitat = make_habitat()
    habitat.max_creatures = 2
    a = add_creature(habitat, "mossnib", 0)
    b = add_creature(habitat, "pebblit", 10)
    assert habitat.is_full

    result = habitat.fuse_creatures(id(a), id(b))

    assert result is not None
    assert len(habitat.creatures) == 1


def test_fusion_key_is_order_independent():
    assert fusion_key("common", "special") == fusion_key("special", "common")


def test_fusing_rarer_creatures_skews_rarity_upward():
    rng = random.Random(42)
    samples = 4000
    common_common_rolls = [
        roll_rarity_for_fusion("common", "common", rng) for _ in range(samples)
    ]
    special_special_rolls = [
        roll_rarity_for_fusion("special", "special", rng) for _ in range(samples)
    ]

    common_special_rate = common_common_rolls.count("special") / samples
    special_special_rate = special_special_rolls.count("special") / samples

    assert special_special_rate > common_special_rate
