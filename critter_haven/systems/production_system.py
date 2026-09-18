"""Converte o tempo passado em ouro contínuo e itens no baú (GDD 6.5)."""

from __future__ import annotations

from critter_haven.economy.chest import Chest
from critter_haven.economy.wallet import Wallet
from critter_haven.entities.creature import Creature


def update_production(
    creatures: list[Creature], dt: float, wallet: Wallet, chest: Chest
) -> None:
    for creature in creatures:
        wallet.add(creature.gold_per_second * dt)
        if creature.tick_item_production(dt):
            chest.add_item(creature.species.item_name, 1)
