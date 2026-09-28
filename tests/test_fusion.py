import random

from critter_haven.data.species import load_planet
from critter_haven.entities.creature import Creature
from critter_haven.entities.habitat import Habitat


def get_species(species_id: str):
    return next(s for s in load_planet("elyndor") if s.id == species_id)


def make_habitat() -> Habitat:
    return Habitat(planet="elyndor", species_pool=load_planet("elyndor"))


def test_has_duplicate_false_with_single_creature():
    habitat = make_habitat()
    habitat.creatures.append(Creature(species=get_species("mossnib"), x=0, y=0))
    assert habitat.has_duplicate("mossnib") is False


def test_has_duplicate_true_with_two_of_same_species():
    habitat = make_habitat()
    habitat.creatures.append(Creature(species=get_species("mossnib"), x=0, y=0))
    habitat.creatures.append(Creature(species=get_species("mossnib"), x=10, y=0))
    assert habitat.has_duplicate("mossnib") is True


def test_release_duplicate_removes_one_and_keeps_the_rest():
    habitat = make_habitat()
    habitat.creatures.append(Creature(species=get_species("mossnib"), x=0, y=0))
    habitat.creatures.append(Creature(species=get_species("mossnib"), x=10, y=0))

    assert habitat.release_duplicate("mossnib") is True
    assert habitat.count_of("mossnib") == 1


def test_release_duplicate_fails_without_a_second_copy():
    habitat = make_habitat()
    habitat.creatures.append(Creature(species=get_species("mossnib"), x=0, y=0))
    assert habitat.release_duplicate("mossnib") is False
    assert habitat.count_of("mossnib") == 1


def test_sacrifice_duplicate_and_spawn_frees_space_and_rolls_new_species():
    habitat = make_habitat()
    habitat.creatures.append(Creature(species=get_species("mossnib"), x=0, y=0))
    habitat.creatures.append(Creature(species=get_species("mossnib"), x=10, y=0))

    result = habitat.sacrifice_duplicate_and_spawn("mossnib")

    assert result is not None
    assert len(habitat.creatures) == 2  # removeu 1 duplicata, sorteou 1 nova


def test_sacrifice_duplicate_fails_without_duplicate():
    habitat = make_habitat()
    habitat.creatures.append(Creature(species=get_species("mossnib"), x=0, y=0))
    assert habitat.sacrifice_duplicate_and_spawn("mossnib") is None
    assert len(habitat.creatures) == 1


def test_sacrifice_can_work_even_when_habitat_is_full():
    habitat = make_habitat()
    habitat.max_creatures = 2
    habitat.creatures.append(Creature(species=get_species("mossnib"), x=0, y=0))
    habitat.creatures.append(Creature(species=get_species("mossnib"), x=10, y=0))
    assert habitat.is_full

    result = habitat.sacrifice_duplicate_and_spawn("mossnib")

    assert result is not None
    assert len(habitat.creatures) == 2
