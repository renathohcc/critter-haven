"""Carrega os dados de combate (Fase 11): estatísticas e habilidade de
cada espécie em batalha, inimigos e as waves de cada planeta."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources


@dataclass(frozen=True)
class UnitStats:
    species_id: str
    role: str  # "tank" | "buffer" | "healer" | "attacker"
    max_hp: float
    damage: float
    range: float
    attack_interval: float
    ability: dict = field(default_factory=dict)


@dataclass(frozen=True)
class EnemyStats:
    enemy_id: str
    name: str
    max_hp: float
    damage: float
    speed: float
    range: float
    attack_interval: float
    boss: bool = False


@dataclass(frozen=True)
class SpawnGroup:
    enemy_id: str
    count: int
    interval: float
    delay: float


@dataclass(frozen=True)
class PlanetDefense:
    planet_id: str
    ship_max_hp: float
    ship_damage: float
    ship_range: float
    ship_attack_interval: float
    waves: tuple[tuple[SpawnGroup, ...], ...]


@dataclass(frozen=True)
class CombatData:
    units: dict[str, UnitStats]
    enemies: dict[str, EnemyStats]
    planets: dict[str, PlanetDefense]


@lru_cache(maxsize=1)
def load_combat_data() -> CombatData:
    raw = resources.files("critter_haven.data").joinpath("combat.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    units = {sid: UnitStats(species_id=sid, **stats) for sid, stats in data["units"].items()}
    enemies = {
        eid: EnemyStats(enemy_id=eid, **stats) for eid, stats in data["enemies"].items()
    }
    planets = {}
    for pid, spec in data["planets"].items():
        ship = spec["ship"]
        waves = tuple(
            tuple(
                SpawnGroup(
                    enemy_id=g["enemy"], count=g["count"], interval=g["interval"], delay=g["delay"]
                )
                for g in wave
            )
            for wave in spec["waves"]
        )
        planets[pid] = PlanetDefense(
            planet_id=pid,
            ship_max_hp=ship["max_hp"],
            ship_damage=ship["damage"],
            ship_range=ship["range"],
            ship_attack_interval=ship["attack_interval"],
            waves=waves,
        )
    return CombatData(units=units, enemies=enemies, planets=planets)
