"""Combatentes da defesa (Fase 11). Python puro, sem pygame -- o desenho
fica pra camada de render. A batalha é 1D: x=0 é a nave (a torre) e x
cresce em direção ao ponto de onde os inimigos entram."""

from __future__ import annotations

from dataclasses import dataclass, field

from critter_haven.data.combat import EnemyStats, UnitStats


@dataclass
class RunModifiers:
    """Multiplicadores da tentativa atual. As cartas rogue-lite (Fase 11.5)
    vão só mexer aqui -- o motor de combate já lê todos."""

    unit_damage: float = 1.0
    unit_hp: float = 1.0
    unit_attack_speed: float = 1.0
    heal: float = 1.0
    enemy_speed: float = 1.0
    ship_max_hp_bonus: float = 0.0
    ship_damage: float = 1.0
    aura_multiplier: float = 1.0
    # multiplicadores por papel ("tank", "attacker"...), somados aos globais
    role_damage: dict = field(default_factory=dict)
    role_hp: dict = field(default_factory=dict)


@dataclass(eq=False)
class Unit:
    uid: int
    stats: UnitStats
    x: float
    hp: float
    max_hp: float
    cooldown: float = 0.0
    ability_timer: float = 0.0
    attacks_made: int = 0

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def role(self) -> str:
        return self.stats.role

    @property
    def taunts(self) -> bool:
        return self.stats.ability.get("type") == "taunt_guard"

    @property
    def damage_reduction(self) -> float:
        if self.stats.ability.get("type") == "taunt_guard":
            return self.stats.ability.get("reduction", 0.0)
        return 0.0


@dataclass(eq=False)
class Enemy:
    uid: int
    stats: EnemyStats
    x: float
    hp: float
    max_hp: float
    cooldown: float = 0.0
    slow_factor: float = 1.0
    slow_timer: float = 0.0

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclass(eq=False)
class Ship:
    max_hp: float
    hp: float
    damage: float
    range: float
    attack_interval: float
    x: float = 0.0
    cooldown: float = 0.0

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclass
class BattleEvent:
    """Registro do que aconteceu num passo -- a camada de render usa pra
    mostrar acertos/curas/mortes; a simulação ignora."""

    kind: str  # "hit" | "heal" | "death" | "wave_start" | "wave_cleared"
    source: int | None = None
    target: int | None = None
    amount: float = 0.0
    extra: dict = field(default_factory=dict)
