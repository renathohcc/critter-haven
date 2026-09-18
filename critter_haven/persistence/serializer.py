"""Conversão entre o estado do jogo e o dicionário salvo em JSON."""

from __future__ import annotations

from datetime import datetime, timezone

from critter_haven.data.species import Species
from critter_haven.economy.chest import Chest
from critter_haven.economy.upgrades import UpgradeManager
from critter_haven.economy.wallet import Wallet
from critter_haven.entities.album import Album
from critter_haven.entities.creature import Creature
from critter_haven.entities.habitat import Habitat

SAVE_VERSION = 1


def build_save_dict(
    wallet: Wallet,
    chest: Chest,
    habitat: Habitat,
    album: Album,
    upgrades: UpgradeManager,
    window_state_name: str,
    always_on_top: bool,
) -> dict:
    return {
        "version": SAVE_VERSION,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "gold": wallet.gold,
        "chest": dict(chest.items),
        "chest_capacity": chest.capacity,
        "discovered": sorted(album.discovered_ids),
        "habitat": {
            "energy": habitat.energy,
            "energy_per_second": habitat.energy_per_second,
            "max_creatures": habitat.max_creatures,
            "creatures": [
                {
                    "species_id": c.species.id,
                    "x": c.x,
                    "item_timer": c.item_timer,
                }
                for c in habitat.creatures
            ],
        },
        "upgrades": dict(upgrades.levels),
        "window_state": window_state_name,
        "always_on_top": always_on_top,
    }


def seconds_since_saved(save_dict: dict) -> float:
    saved_at = datetime.fromisoformat(save_dict["saved_at"])
    now = datetime.now(timezone.utc)
    return max(0.0, (now - saved_at).total_seconds())


def restore_from_save(
    save_dict: dict,
    species_by_id: dict[str, Species],
    wallet: Wallet,
    chest: Chest,
    habitat: Habitat,
    album: Album,
    upgrades: UpgradeManager,
) -> float:
    """Aplica o save aos objetos de estado (em memória) e retorna quantos
    segundos se passaram desde o último save, para o cálculo offline."""
    wallet.gold = save_dict.get("gold", 0.0)

    chest.items = dict(save_dict.get("chest", {}))
    chest.capacity = save_dict.get("chest_capacity", chest.capacity)

    for species_id in save_dict.get("discovered", []):
        if species_id in species_by_id:
            album.discovered_ids.add(species_id)

    habitat_data = save_dict.get("habitat", {})
    habitat.energy = habitat_data.get("energy", 0.0)
    habitat.energy_per_second = habitat_data.get(
        "energy_per_second", habitat.energy_per_second
    )
    habitat.max_creatures = habitat_data.get("max_creatures", habitat.max_creatures)
    habitat.creatures.clear()
    for creature_data in habitat_data.get("creatures", []):
        species = species_by_id.get(creature_data["species_id"])
        if species is None:
            continue
        creature = Creature(
            species=species, x=creature_data.get("x", 0.0), y=habitat.spawn_y
        )
        creature.item_timer = creature_data.get("item_timer", creature.item_timer)
        habitat.creatures.append(creature)

    upgrades.levels = dict(save_dict.get("upgrades", {}))

    return seconds_since_saved(save_dict)
