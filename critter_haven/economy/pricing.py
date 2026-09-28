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


def sell_item(
    chest: Chest, wallet: Wallet, price_map: dict[str, float], item_name: str, quantity: int
) -> float:
    """Vende só `quantity` unidades de `item_name` (o Baú agora deixa
    escolher item e quantidade em vez de só "vender tudo"). Vende no
    máximo o que existe no baú; retorna 0.0 sem alterar nada se o item
    não existir ou a quantidade pedida não for positiva."""
    available = chest.items.get(item_name, 0)
    qty = min(quantity, available)
    if qty <= 0:
        return 0.0
    total = price_map.get(item_name, 0.0) * qty
    remaining = available - qty
    if remaining > 0:
        chest.items[item_name] = remaining
    else:
        del chest.items[item_name]
    wallet.add(total)
    return total
