"""Cartas rogue-lite da defesa (Fase 11.5): ao fim de cada wave o jogador
escolhe 1 de 3. Valem só na tentativa atual (mexem no `RunModifiers` do
`Battle`). Dados em data/cards.json; aqui só carregar, sortear e aplicar.
Python puro."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

from critter_haven.systems.combat_system import Battle

CHOICES_PER_WAVE = 3
RARE_WEIGHT = 0.3


@dataclass(frozen=True)
class Card:
    card_id: str
    name: str
    description: str
    rarity: str  # "common" | "rare"
    effects: tuple[dict, ...]


@lru_cache(maxsize=1)
def load_cards() -> tuple[Card, ...]:
    raw = resources.files("critter_haven.data").joinpath("cards.json").read_text(encoding="utf-8")
    return tuple(
        Card(
            card_id=c["id"],
            name=c["name"],
            description=c["description"],
            rarity=c["rarity"],
            effects=tuple(c["effects"]),
        )
        for c in json.loads(raw)["cards"]
    )


def card_by_id(card_id: str) -> Card:
    return next(c for c in load_cards() if c.card_id == card_id)


def draw_choices(
    rng: random.Random, taken_ids: list[str] | tuple[str, ...] = (), count: int = CHOICES_PER_WAVE
) -> list[Card]:
    """Sorteia `count` cartas distintas, sem repetir as que já foram
    escolhidas nesta tentativa (a não ser que o baralho acabe)."""
    pool = [c for c in load_cards() if c.card_id not in taken_ids]
    if len(pool) < count:
        pool = list(load_cards())
    chosen: list[Card] = []
    while len(chosen) < count and pool:
        rare = rng.random() < RARE_WEIGHT
        tier = [c for c in pool if (c.rarity == "rare") == rare] or pool
        card = rng.choice(tier)
        chosen.append(card)
        pool.remove(card)
    return chosen


def apply_card(battle: Battle, card: Card) -> None:
    mods = battle.modifiers
    for effect in card.effects:
        kind = effect["type"]
        if kind == "mod":
            setattr(mods, effect["field"], getattr(mods, effect["field"]) * effect["mult"])
        elif kind == "role_mod":
            table = getattr(mods, effect["field"])
            table[effect["role"]] = table.get(effect["role"], 1.0) * effect["mult"]
        elif kind == "ship_hp_bonus":
            mods.ship_max_hp_bonus += effect["amount"]
        elif kind == "heal_ship":
            battle.heal_ship_fraction(effect["fraction"])
        elif kind == "heal_units":
            battle.heal_units_fraction(effect["fraction"])
    battle.refresh_stats()


def run_battle_with_cards(
    planet_id: str,
    army: list[str],
    seed: int = 0,
    dt: float = 0.1,
    max_seconds: float = 3600.0,
    picker=None,
) -> tuple[Battle, list[str]]:
    """Como `run_battle`, mas oferece 3 cartas entre as waves (o `picker`
    escolhe uma das ofertadas; padrão: aleatória). Usado pelo simulador."""
    from critter_haven.data.combat import load_combat_data

    battle = Battle(load_combat_data().planets[planet_id], army, seed=seed)
    picked: list[str] = []
    battle.start_next_wave()
    while battle.phase in ("wave", "between_waves") and battle.time < max_seconds:
        if battle.phase == "between_waves":
            options = draw_choices(battle.rng, picked)
            choice = picker(options, battle) if picker else battle.rng.choice(options)
            apply_card(battle, choice)
            picked.append(choice.card_id)
            battle.start_next_wave()
        battle.step(dt)
    return battle, picked
