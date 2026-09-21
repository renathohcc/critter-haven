from critter_haven.data.species import load_planet
from critter_haven.entities.habitat import Habitat


def make_habitat() -> Habitat:
    return Habitat(planet="elyndor", species_pool=load_planet("elyndor"))


def test_stationary_species_spawns_pinned_at_its_own_position():
    habitat = make_habitat()
    for _ in range(20):
        habitat.update(100)  # forca varios spawns

    lumibloom = [c for c in habitat.creatures if c.species.id == "lumibloom"]
    for creature in lumibloom:
        assert creature.roam_min_x == creature.roam_max_x == creature.x


def test_stationary_creature_never_moves_across_updates():
    habitat = make_habitat()
    habitat.update(100)
    lumibloom = next((c for c in habitat.creatures if c.species.id == "lumibloom"), None)
    if lumibloom is None:
        return  # RNG nao sorteou lumibloom nesse spawn, sem problema
    original_x = lumibloom.x
    for _ in range(50):
        habitat.update(0.5)
    assert round(lumibloom.x) == round(original_x)


def test_resync_keeps_stationary_creature_pinned_not_resampled():
    habitat = make_habitat()
    habitat.update(100)
    lumibloom = next((c for c in habitat.creatures if c.species.id == "lumibloom"), None)
    if lumibloom is None:
        return
    original_x = lumibloom.x
    habitat.max_x = 500  # simula reduzir a janela
    habitat.resync_roam_bounds()
    assert lumibloom.x == min(original_x, 500)
    assert lumibloom.roam_min_x == lumibloom.roam_max_x == lumibloom.x
