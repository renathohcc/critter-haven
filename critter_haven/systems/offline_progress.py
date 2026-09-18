"""Progresso enquanto o jogo está fechado (GDD 6.10). Calculado
analiticamente a partir do tempo decorrido — nunca simulando o jogo
tick a tick — para não travar a abertura do jogo depois de horas
offline. O tempo é limitado a MAX_OFFLINE_SECONDS para não conceder
recursos ilimitados caso o relógio do sistema seja adulterado."""

from __future__ import annotations

from critter_haven.config.economy import ITEM_INTERVAL_BY_RARITY
from critter_haven.config.spawn import ENERGY_MAX
from critter_haven.economy.chest import Chest
from critter_haven.economy.wallet import Wallet
from critter_haven.entities.album import Album
from critter_haven.entities.habitat import Habitat

MAX_OFFLINE_SECONDS = 12 * 60 * 60  # 12h


def apply_offline_progress(
    habitat: Habitat,
    wallet: Wallet,
    chest: Chest,
    album: Album,
    gold_multiplier: float,
    elapsed_seconds: float,
) -> dict:
    elapsed = max(0.0, min(elapsed_seconds, MAX_OFFLINE_SECONDS))

    gold_gain = (
        sum(c.gold_per_second for c in habitat.creatures) * gold_multiplier * elapsed
    )
    wallet.add(gold_gain)

    items_gained: dict[str, int] = {}
    for creature in habitat.creatures:
        interval = ITEM_INTERVAL_BY_RARITY[creature.rarity]
        time_available = elapsed + (interval - creature.item_timer)
        count = int(time_available // interval)
        for _ in range(count):
            if chest.add_item(creature.species.item_name, 1):
                items_gained[creature.species.item_name] = (
                    items_gained.get(creature.species.item_name, 0) + 1
                )
        creature.item_timer = interval - (time_available % interval)

    spawned_names: list[str] = []
    total_energy = habitat.energy + habitat.energy_per_second * elapsed
    while total_energy >= ENERGY_MAX and not habitat.is_full:
        species = habitat.spawn_one()
        album.register(species)
        spawned_names.append(species.name)
        total_energy -= ENERGY_MAX
    habitat.energy = min(total_energy, ENERGY_MAX)

    return {
        "elapsed_seconds": elapsed,
        "gold_gain": gold_gain,
        "items_gained": items_gained,
        "spawned_names": spawned_names,
    }
