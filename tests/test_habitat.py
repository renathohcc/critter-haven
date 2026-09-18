from critter_haven.config.spawn import ENERGY_MAX, ENERGY_PER_SECOND
from critter_haven.data.species import load_planet
from critter_haven.entities.habitat import Habitat


def make_habitat() -> Habitat:
    return Habitat(planet="elyndor", species_pool=load_planet("elyndor"))


def test_energy_accumulates_and_spawns_on_max():
    habitat = make_habitat()
    seconds_to_fill = ENERGY_MAX / ENERGY_PER_SECOND

    spawned = None
    for _ in range(int(seconds_to_fill) - 1):
        spawned = habitat.update(1.0)
    assert spawned is None
    assert len(habitat.creatures) == 0

    spawned = habitat.update(2.0)
    assert spawned is not None
    assert len(habitat.creatures) == 1
    assert habitat.energy == 0.0


def test_creature_at_hits_within_radius():
    habitat = make_habitat()
    habitat.update(100)  # forca spawn
    creature = habitat.creatures[0]
    found = habitat.creature_at(creature.x, creature.y)
    assert found is creature


def test_creature_at_misses_far_away():
    habitat = make_habitat()
    habitat.update(100)
    found = habitat.creature_at(-9999, -9999)
    assert found is None


def test_spawn_stops_at_max_creatures_and_holds_energy():
    habitat = make_habitat()
    habitat.max_creatures = 2

    for _ in range(2):
        habitat.update(100)  # cada chamada forca um spawn
    assert len(habitat.creatures) == 2
    assert habitat.is_full

    spawned = habitat.update(100)
    assert spawned is None
    assert len(habitat.creatures) == 2
    assert habitat.energy == ENERGY_MAX  # energia represada, nao perdida


def test_spawn_resumes_after_freeing_space():
    habitat = make_habitat()
    habitat.max_creatures = 1
    habitat.update(100)
    assert habitat.is_full

    habitat.update(100)  # segue represando energia
    habitat.creatures.clear()

    spawned = habitat.update(0.0)
    assert spawned is not None
    assert len(habitat.creatures) == 1
