"""Ouro acumulado do jogador."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Wallet:
    gold: float = 0.0

    def add(self, amount: float) -> None:
        if amount > 0:
            self.gold += amount

    def can_afford(self, amount: float) -> bool:
        return self.gold >= amount

    def spend(self, amount: float) -> bool:
        if not self.can_afford(amount):
            return False
        self.gold -= amount
        return True
