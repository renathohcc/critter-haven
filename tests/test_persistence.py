from datetime import datetime, timedelta, timezone

from critter_haven.data.species import all_species_by_id, load_planet
from critter_haven.economy.chest import Chest
from critter_haven.economy.upgrades import UpgradeManager
from critter_haven.economy.wallet import Wallet
from critter_haven.entities.album import Album
from critter_haven.entities.creature import Creature
from critter_haven.entities.habitat import Habitat
from critter_haven.persistence.save_file import load_game, save_game
from critter_haven.persistence.serializer import (
    build_save_dict,
    restore_from_save,
    seconds_since_saved,
)


def make_state():
    species_pool = load_planet("elyndor")
    habitat = Habitat(planet="elyndor", species_pool=species_pool)
    wallet = Wallet(gold=500)
    chest = Chest()
    album = Album()
    upgrades = UpgradeManager()
    return species_pool, habitat, wallet, chest, album, upgrades


def test_build_and_restore_round_trip():
    species_pool, habitat, wallet, chest, album, upgrades = make_state()
    mossnib = species_pool[0]
    habitat.creatures.append(Creature(species=mossnib, x=42.0, y=habitat.spawn_y))
    album.register(mossnib)
    chest.add_item("Folha Viva", 3)
    upgrades.levels["gold_production"] = 2

    save_dict = build_save_dict(wallet, chest, habitat, album, upgrades, "medium", True)

    new_species_pool, new_habitat, new_wallet, new_chest, new_album, new_upgrades = make_state()
    elapsed = restore_from_save(
        save_dict,
        all_species_by_id(),
        new_wallet,
        new_chest,
        new_habitat,
        new_album,
        new_upgrades,
    )

    assert new_wallet.gold == 500
    assert new_chest.items == {"Folha Viva": 3}
    assert new_album.is_discovered(mossnib)
    assert len(new_habitat.creatures) == 1
    assert new_habitat.creatures[0].x == 42.0
    assert new_upgrades.level("gold_production") == 2
    assert elapsed >= 0


def test_seconds_since_saved_computes_elapsed_time():
    saved_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    elapsed = seconds_since_saved({"saved_at": saved_at})
    assert 290 <= elapsed <= 310


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "save.json"
    data = {"version": 1, "saved_at": "2026-01-01T00:00:00+00:00", "gold": 42}
    save_game(data, path)
    loaded = load_game(path)
    assert loaded == data


def test_load_missing_file_returns_none(tmp_path):
    assert load_game(tmp_path / "does_not_exist.json") is None


def test_load_corrupted_file_returns_none(tmp_path):
    path = tmp_path / "save.json"
    path.write_text("{not valid json", encoding="utf-8")
    assert load_game(path) is None


def test_load_file_without_version_key_returns_none(tmp_path):
    path = tmp_path / "save.json"
    path.write_text('{"gold": 10}', encoding="utf-8")
    assert load_game(path) is None
