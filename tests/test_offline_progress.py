from critter_haven.config.spawn import ENERGY_MAX
from critter_haven.data.species import load_planet
from critter_haven.economy.chest import Chest
from critter_haven.economy.wallet import Wallet
from critter_haven.entities.album import Album
from critter_haven.entities.creature import Creature
from critter_haven.entities.habitat import Habitat
from critter_haven.systems.offline_progress import (
    MAX_OFFLINE_SECONDS,
    apply_offline_progress,
)


def get_species(species_id: str):
    return next(s for s in load_planet("elyndor") if s.id == species_id)


def make_habitat_with_creature(species_id: str) -> Habitat:
    species_pool = load_planet("elyndor")
    habitat = Habitat(planet="elyndor", species_pool=species_pool)
    habitat.creatures.append(
        Creature(species=get_species(species_id), x=0, y=habitat.spawn_y)
    )
    return habitat


def test_gold_gain_scales_with_elapsed_time():
    habitat = make_habitat_with_creature("mossnib")
    wallet = Wallet()
    chest = Chest()
    album = Album()

    result = apply_offline_progress(habitat, wallet, chest, album, 1.0, 100.0)

    assert result["gold_gain"] == 12 * 100.0
    assert wallet.gold == 12 * 100.0


def test_gold_gain_respects_multiplier():
    habitat = make_habitat_with_creature("mossnib")
    wallet = Wallet()
    chest = Chest()
    album = Album()

    apply_offline_progress(habitat, wallet, chest, album, 2.0, 10.0)

    assert wallet.gold == 12 * 10.0 * 2.0


def test_elapsed_time_is_capped_at_max_offline_seconds():
    habitat = make_habitat_with_creature("mossnib")
    wallet = Wallet()
    chest = Chest()
    album = Album()

    result = apply_offline_progress(
        habitat, wallet, chest, album, 1.0, MAX_OFFLINE_SECONDS * 10
    )

    assert result["elapsed_seconds"] == MAX_OFFLINE_SECONDS


def test_items_are_produced_during_offline_time():
    habitat = make_habitat_with_creature("mossnib")  # comum -> intervalo 8s
    wallet = Wallet()
    chest = Chest()
    album = Album()

    result = apply_offline_progress(habitat, wallet, chest, album, 1.0, 20.0)

    assert result["items_gained"] == {"Folha Viva": 2}
    assert chest.items["Folha Viva"] == 2


def test_spawns_happen_when_energy_overflows_offline():
    species_pool = load_planet("elyndor")
    habitat = Habitat(planet="elyndor", species_pool=species_pool, energy_per_second=1.0)
    wallet = Wallet()
    chest = Chest()
    album = Album()

    result = apply_offline_progress(habitat, wallet, chest, album, 1.0, ENERGY_MAX * 2.5)

    assert len(habitat.creatures) == 2
    assert len(result["spawned_names"]) == 2
    assert habitat.energy < ENERGY_MAX


def test_spawns_stop_when_habitat_is_full():
    species_pool = load_planet("elyndor")
    habitat = Habitat(
        planet="elyndor", species_pool=species_pool, energy_per_second=1.0, max_creatures=1
    )
    wallet = Wallet()
    chest = Chest()
    album = Album()

    apply_offline_progress(habitat, wallet, chest, album, 1.0, ENERGY_MAX * 5)

    assert len(habitat.creatures) == 1


def test_discovered_species_are_registered_in_album():
    species_pool = load_planet("elyndor")
    habitat = Habitat(planet="elyndor", species_pool=species_pool, energy_per_second=1.0)
    wallet = Wallet()
    chest = Chest()
    album = Album()

    apply_offline_progress(habitat, wallet, chest, album, 1.0, ENERGY_MAX)

    assert len(album.discovered_ids) == 1
