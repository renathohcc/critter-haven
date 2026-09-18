"""Verificação de requisitos de viagem entre planetas (GDD seção 7)."""

from __future__ import annotations

from critter_haven.config.planets import PlanetDestination
from critter_haven.economy.chest import Chest


def can_travel(destination: PlanetDestination, chest: Chest) -> bool:
    if destination.active:
        return True
    if destination.requirement_pending or destination.required_item is None:
        return False
    return chest.items.get(destination.required_item, 0) >= destination.required_quantity


def travel(destination: PlanetDestination, chest: Chest) -> bool:
    if not can_travel(destination, chest):
        return False
    if destination.required_item:
        chest.items[destination.required_item] -= destination.required_quantity
        if chest.items[destination.required_item] <= 0:
            del chest.items[destination.required_item]
    return True
