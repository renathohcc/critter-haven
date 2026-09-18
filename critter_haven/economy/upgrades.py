"""Estado e regras de compra dos upgrades (GDD 6.6)."""

from __future__ import annotations

from dataclasses import dataclass, field

from critter_haven.config.upgrades import UpgradeDef
from critter_haven.economy.wallet import Wallet


@dataclass
class UpgradeManager:
    levels: dict[str, int] = field(default_factory=dict)

    def level(self, upgrade_id: str) -> int:
        return self.levels.get(upgrade_id, 0)

    def is_maxed(self, upgrade: UpgradeDef) -> bool:
        return self.level(upgrade.id) >= upgrade.max_level

    def cost(self, upgrade: UpgradeDef) -> float | None:
        if self.is_maxed(upgrade):
            return None
        return round(upgrade.base_cost * (upgrade.cost_growth ** self.level(upgrade.id)), 2)

    def buy(self, upgrade: UpgradeDef, wallet: Wallet) -> bool:
        cost = self.cost(upgrade)
        if cost is None or not wallet.spend(cost):
            return False
        self.levels[upgrade.id] = self.level(upgrade.id) + 1
        return True

    def effect_total(self, upgrade: UpgradeDef) -> float:
        return self.level(upgrade.id) * upgrade.effect_per_level
