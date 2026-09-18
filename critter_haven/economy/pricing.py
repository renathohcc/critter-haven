"""Preço de venda dos itens e conversão do baú em ouro."""

from __future__ import annotations

from critter_haven.config.economy import ITEM_SELL_PRICE_FACTOR
from critter_haven.data.species import Species
from critter_haven.economy.chest import Chest
from critter_haven.economy.wallet import Wallet


def item_price(species: Species) -> float:
    return round(species.base_gold_per_second * ITEM_SELL_PRICE_FACTOR, 2)


def build_price_map(species_list: list[Species]) -> dict[str, float]:
    return {species.item_name: item_price(species) for species in species_list}


def sell_all(chest: Chest, wallet: Wallet, price_map: dict[str, float]) -> float:
    total = sum(price_map.get(name, 0.0) * qty for name, qty in chest.items.items())
    wallet.add(total)
    chest.clear()
    return total
