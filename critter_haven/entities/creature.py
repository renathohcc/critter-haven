"""Entidade Criatura: estado e comportamento, sem nenhuma dependência visual."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from critter_haven.config.economy import ITEM_INTERVAL_BY_RARITY
from critter_haven.data.species import Species

WANDER_SPEED = 18.0  # pixels/segundo
CLICK_FEEDBACK_DURATION = 0.4


@dataclass(eq=False)
class Creature:
    species: Species
    x: float
    y: float
    direction: int = 1
    move_timer: float = 0.0
    click_feedback_timer: float = 0.0
    item_timer: float = field(default=0.0)
    item_feedback_timer: float = 0.0

    def __post_init__(self) -> None:
        if self.item_timer <= 0:
            self.item_timer = ITEM_INTERVAL_BY_RARITY[self.species.rarity]

    @property
    def rarity(self) -> str:
        return self.species.rarity

    @property
    def gold_per_second(self) -> float:
        # base_gold_per_second no JSON já é o valor final documentado no GDD
        # (o multiplicador de raridade está embutido nos valores por espécie).
        return self.species.base_gold_per_second

    def update(self, dt: float, min_x: float, max_x: float) -> None:
        self.move_timer -= dt
        if self.move_timer <= 0:
            self.direction = random.choice((-1, 1))
            self.move_timer = random.uniform(1.5, 4.0)

        self.x += self.direction * WANDER_SPEED * dt
        if self.x < min_x:
            self.x, self.direction = min_x, 1
        elif self.x > max_x:
            self.x, self.direction = max_x, -1

        if self.click_feedback_timer > 0:
            self.click_feedback_timer = max(0.0, self.click_feedback_timer - dt)
        if self.item_feedback_timer > 0:
            self.item_feedback_timer = max(0.0, self.item_feedback_timer - dt)

    def on_click(self) -> None:
        self.click_feedback_timer = CLICK_FEEDBACK_DURATION

    def is_clicked_feedback_active(self) -> bool:
        return self.click_feedback_timer > 0

    def tick_item_production(self, dt: float) -> bool:
        """Retorna True quando a criatura solta um item nesta atualização."""
        self.item_timer -= dt
        if self.item_timer > 0:
            return False
        self.item_timer += ITEM_INTERVAL_BY_RARITY[self.species.rarity]
        self.item_feedback_timer = CLICK_FEEDBACK_DURATION
        return True

    def is_item_feedback_active(self) -> bool:
        return self.item_feedback_timer > 0
