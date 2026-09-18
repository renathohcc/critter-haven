"""Baú de Homie: itens acumulados pelas criaturas, com capacidade limitada
(upgrades de armazenamento na Fase 4 devem aumentar `capacity` em runtime)."""

from __future__ import annotations

from dataclasses import dataclass, field

from critter_haven.config.economy import BASE_CHEST_CAPACITY


@dataclass
class Chest:
    capacity: int = BASE_CHEST_CAPACITY
    items: dict[str, int] = field(default_factory=dict)

    def total_count(self) -> int:
        return sum(self.items.values())

    @property
    def is_full(self) -> bool:
        return self.total_count() >= self.capacity

    def add_item(self, item_name: str, quantity: int = 1) -> bool:
        if self.is_full:
            return False
        self.items[item_name] = self.items.get(item_name, 0) + quantity
        return True

    def clear(self) -> dict[str, int]:
        removed = dict(self.items)
        self.items.clear()
        return removed
