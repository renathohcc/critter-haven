"""Motor de combate da defesa do planeta (Fase 11.1). Python puro:
roda em passos fixos de tempo, sem pygame, então é testável em
milissegundos e dá pra simular centenas de batalhas (ver
scripts/simulate_combat.py).

Regras principais:
- Unidades ficam paradas na posição do seu papel (tanque à frente, healer
  e buffer atrás) e atacam o inimigo mais próximo ao alcance.
- Inimigos andam em direção à nave e param pra atacar o primeiro alvo ao
  alcance; unidades com "taunt" têm prioridade sobre as demais.
- Entre waves as unidades se recuperam (e as caídas revivem): derrota/
  vitória da batalha nunca tira criaturas do habitat.
"""

from __future__ import annotations

import random

from critter_haven.data.combat import CombatData, PlanetDefense, load_combat_data
from critter_haven.entities.combatants import (
    BattleEvent,
    Enemy,
    RunModifiers,
    Ship,
    Unit,
)

FIELD_LENGTH = 700.0  # onde os inimigos entram
ROLE_SLOT_X = {"healer": 70.0, "buffer": 125.0, "attacker": 195.0, "tank": 285.0}
SLOT_SPACING = 22.0

SURVIVOR_HEAL_FRACTION = 0.3
REVIVE_HP_FRACTION = 0.5
SHIP_HEAL_BETWEEN_WAVES = 0.15


class Battle:
    def __init__(
        self,
        defense: PlanetDefense,
        army: list[str],
        modifiers: RunModifiers | None = None,
        seed: int = 0,
        data: CombatData | None = None,
    ) -> None:
        self.data = data or load_combat_data()
        self.defense = defense
        self.modifiers = modifiers or RunModifiers()
        self.rng = random.Random(seed)
        self._next_uid = 1

        max_hp = defense.ship_max_hp + self.modifiers.ship_max_hp_bonus
        self.ship = Ship(
            max_hp=max_hp,
            hp=max_hp,
            damage=defense.ship_damage,
            range=defense.ship_range,
            attack_interval=defense.ship_attack_interval,
        )
        self.units: list[Unit] = self._build_units(army)
        self.enemies: list[Enemy] = []

        self.wave_index = -1  # nenhuma wave iniciada ainda
        self.phase = "ready"  # ready | wave | between_waves | won | lost
        self.time = 0.0
        self.wave_time = 0.0
        self._spawn_queue: list[tuple[float, str]] = []
        self.events: list[BattleEvent] = []

    # ------------------------------------------------------------ montagem
    def _uid(self) -> int:
        uid = self._next_uid
        self._next_uid += 1
        return uid

    def _build_units(self, army: list[str]) -> list[Unit]:
        by_role: dict[str, list[str]] = {}
        for species_id in army:
            stats = self.data.units.get(species_id)
            if stats is not None:
                by_role.setdefault(stats.role, []).append(species_id)
        units = []
        for role, ids in by_role.items():
            base_x = ROLE_SLOT_X[role]
            for i, species_id in enumerate(ids):
                stats = self.data.units[species_id]
                hp = stats.max_hp * self.modifiers.unit_hp * self.modifiers.role_hp.get(role, 1.0)
                units.append(
                    Unit(
                        uid=self._uid(),
                        stats=stats,
                        x=base_x + i * SLOT_SPACING,
                        hp=hp,
                        max_hp=hp,
                        cooldown=self.rng.uniform(0, stats.attack_interval),
                    )
                )
        return units

    # ------------------------------------------------------------- waves
    @property
    def total_waves(self) -> int:
        return len(self.defense.waves)

    @property
    def is_last_wave(self) -> bool:
        return self.wave_index == self.total_waves - 1

    def start_next_wave(self) -> None:
        if self.phase not in ("ready", "between_waves"):
            return
        self.wave_index += 1
        queue: list[tuple[float, str]] = []
        for group in self.defense.waves[self.wave_index]:
            for i in range(group.count):
                queue.append((group.delay + i * group.interval, group.enemy_id))
        queue.sort(key=lambda item: item[0])
        self._spawn_queue = queue
        self.wave_time = 0.0
        self.phase = "wave"
        self.events.append(BattleEvent("wave_start", extra={"wave": self.wave_index}))

    def _recover_between_waves(self) -> None:
        for unit in self.units:
            if unit.alive:
                unit.hp = min(unit.max_hp, unit.hp + unit.max_hp * SURVIVOR_HEAL_FRACTION)
            else:
                unit.hp = unit.max_hp * REVIVE_HP_FRACTION
            unit.cooldown = 0.0
        self.ship.hp = min(self.ship.max_hp, self.ship.hp + self.ship.max_hp * SHIP_HEAL_BETWEEN_WAVES)

    # ----------------------------------------------------------- cartas
    def refresh_stats(self) -> None:
        """Reaplica os modificadores da tentativa (chamado quando uma carta
        muda vida máxima): vida atual acompanha a máxima, proporcional."""
        for unit in self.units:
            new_max = (
                unit.stats.max_hp
                * self.modifiers.unit_hp
                * self.modifiers.role_hp.get(unit.role, 1.0)
            )
            if new_max != unit.max_hp:
                ratio = unit.hp / unit.max_hp if unit.max_hp else 1.0
                unit.max_hp = new_max
                unit.hp = new_max * ratio if unit.alive else 0.0
        new_ship_max = self.defense.ship_max_hp + self.modifiers.ship_max_hp_bonus
        if new_ship_max != self.ship.max_hp:
            self.ship.hp += new_ship_max - self.ship.max_hp
            self.ship.max_hp = new_ship_max

    def heal_ship_fraction(self, fraction: float) -> None:
        self.ship.hp = min(self.ship.max_hp, self.ship.hp + self.ship.max_hp * fraction)

    def heal_units_fraction(self, fraction: float) -> None:
        for unit in self.units:
            if unit.alive:
                unit.hp = min(unit.max_hp, unit.hp + unit.max_hp * fraction)

    # --------------------------------------------------------------- passo
    def step(self, dt: float) -> None:
        self.events = []
        if self.phase != "wave":
            return
        self.time += dt
        self.wave_time += dt

        self._spawn()
        self._tick_status(dt)
        aura = self._damage_aura_bonus()
        self._units_act(dt, aura)
        self._enemies_act(dt)
        self._ship_act(dt)
        self._cleanup()

        if not self.ship.alive:
            self.phase = "lost"
        elif not self._spawn_queue and not self.enemies:
            self.events.append(BattleEvent("wave_cleared", extra={"wave": self.wave_index}))
            if self.is_last_wave:
                self.phase = "won"
            else:
                self._recover_between_waves()
                self.phase = "between_waves"

    def _spawn(self) -> None:
        while self._spawn_queue and self._spawn_queue[0][0] <= self.wave_time:
            _t, enemy_id = self._spawn_queue.pop(0)
            stats = self.data.enemies[enemy_id]
            self.enemies.append(
                Enemy(uid=self._uid(), stats=stats, x=FIELD_LENGTH, hp=stats.max_hp, max_hp=stats.max_hp)
            )

    def _tick_status(self, dt: float) -> None:
        for enemy in self.enemies:
            if enemy.slow_timer > 0:
                enemy.slow_timer -= dt
                if enemy.slow_timer <= 0:
                    enemy.slow_factor = 1.0

    def _damage_aura_bonus(self) -> dict[int, float]:
        bonus: dict[int, float] = {u.uid: 0.0 for u in self.units}
        for buffer in self.units:
            ability = buffer.stats.ability
            if buffer.alive and ability.get("type") == "damage_aura":
                for other in self.units:
                    if other is not buffer and other.alive and abs(other.x - buffer.x) <= ability["radius"]:
                        bonus[other.uid] += ability["bonus"] * self.modifiers.aura_multiplier
        return bonus

    # ------------------------------------------------------------ unidades
    def _units_act(self, dt: float, aura: dict[int, float]) -> None:
        for unit in self.units:
            if not unit.alive:
                continue
            if unit.stats.ability.get("type") == "heal":
                self._healer_act(unit, dt)
            if unit.stats.damage <= 0:
                continue
            unit.cooldown -= dt
            if unit.cooldown > 0:
                continue
            target = self._nearest_enemy(unit.x, unit.stats.range)
            if target is None:
                unit.cooldown = 0.0
                continue
            damage = (
                unit.stats.damage
                * self.modifiers.unit_damage
                * self.modifiers.role_damage.get(unit.role, 1.0)
                * (1.0 + aura[unit.uid])
            )
            self._hit_enemy(unit, target, damage)
            unit.attacks_made += 1
            unit.cooldown += unit.stats.attack_interval / self.modifiers.unit_attack_speed

    def _healer_act(self, healer: Unit, dt: float) -> None:
        ability = healer.stats.ability
        healer.ability_timer -= dt
        if healer.ability_timer > 0:
            return
        candidates = [
            u for u in self.units
            if u.alive and u.hp < u.max_hp and abs(u.x - healer.x) <= healer.stats.range
        ]
        if (
            self.ship.alive
            and self.ship.hp < self.ship.max_hp
            and abs(self.ship.x - healer.x) <= healer.stats.range
        ):
            candidates.append(self.ship)
        if not candidates:
            healer.ability_timer = 0.0
            return
        target = min(candidates, key=lambda c: c.hp / c.max_hp)
        amount = ability["amount"] * self.modifiers.heal
        target.hp = min(target.max_hp, target.hp + amount)
        healer.ability_timer = ability["interval"]
        self.events.append(
            BattleEvent("heal", source=healer.uid, target=getattr(target, "uid", 0), amount=amount)
        )

    def _nearest_enemy(self, x: float, reach: float) -> Enemy | None:
        best = None
        best_dist = reach
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            dist = abs(enemy.x - x)
            if dist <= best_dist:
                best, best_dist = enemy, dist
        return best

    def _hit_enemy(self, source: Unit, target: Enemy, damage: float) -> None:
        target.hp -= damage
        self.events.append(BattleEvent("hit", source=source.uid, target=target.uid, amount=damage))
        ability = source.stats.ability
        kind = ability.get("type")
        if kind == "slow_hit":
            target.slow_factor = 1.0 - ability["slow"]
            target.slow_timer = ability["duration"]
        elif kind == "splash":
            for other in self.enemies:
                if other is not target and other.alive and abs(other.x - target.x) <= ability["radius"]:
                    other.hp -= damage * ability["fraction"]

    # ------------------------------------------------------------ inimigos
    def _enemies_act(self, dt: float) -> None:
        taunters = [u for u in self.units if u.alive and u.taunts]
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            target = self._enemy_target(enemy, taunters)
            if target is not None:
                enemy.cooldown -= dt
                if enemy.cooldown <= 0:
                    self._hit_ally(enemy, target)
                    enemy.cooldown += enemy.stats.attack_interval
            else:
                speed = enemy.stats.speed * enemy.slow_factor * self.modifiers.enemy_speed
                enemy.x = max(self.ship.x + 1.0, enemy.x - speed * dt)
                enemy.cooldown = 0.0

    def _enemy_target(self, enemy: Enemy, taunters: list[Unit]):
        reach = enemy.stats.range
        in_reach = [t for t in taunters if abs(t.x - enemy.x) <= reach]
        if in_reach:
            return min(in_reach, key=lambda t: abs(t.x - enemy.x))
        candidates = [u for u in self.units if u.alive and abs(u.x - enemy.x) <= reach]
        if self.ship.alive and abs(self.ship.x - enemy.x) <= reach:
            candidates.append(self.ship)
        if not candidates:
            return None
        return min(candidates, key=lambda t: abs(t.x - enemy.x))

    def _hit_ally(self, enemy: Enemy, target) -> None:
        damage = enemy.stats.damage
        if isinstance(target, Unit):
            damage *= 1.0 - target.damage_reduction
        target.hp -= damage
        self.events.append(
            BattleEvent("hit", source=enemy.uid, target=getattr(target, "uid", 0), amount=damage)
        )

    # ---------------------------------------------------------------- nave
    def _ship_act(self, dt: float) -> None:
        if not self.ship.alive or self.ship.damage <= 0:
            return
        self.ship.cooldown -= dt
        if self.ship.cooldown > 0:
            return
        target = self._nearest_enemy(self.ship.x, self.ship.range)
        if target is None:
            self.ship.cooldown = 0.0
            return
        damage = self.ship.damage * self.modifiers.ship_damage
        target.hp -= damage
        self.events.append(BattleEvent("hit", source=0, target=target.uid, amount=damage))
        self.ship.cooldown += self.ship.attack_interval

    def _cleanup(self) -> None:
        for enemy in self.enemies:
            if not enemy.alive:
                self.events.append(BattleEvent("death", target=enemy.uid))
        self.enemies = [e for e in self.enemies if e.alive]
        for unit in self.units:
            if not unit.alive and unit.hp != 0.0:
                unit.hp = 0.0
                self.events.append(BattleEvent("death", target=unit.uid))


def run_battle(
    planet_id: str,
    army: list[str],
    modifiers: RunModifiers | None = None,
    seed: int = 0,
    dt: float = 0.1,
    max_seconds: float = 3600.0,
) -> Battle:
    """Roda a defesa inteira até vitória/derrota (usado pelo simulador e
    pelos testes). Sem cartas: avança direto de uma wave pra próxima."""
    battle = Battle(load_combat_data().planets[planet_id], army, modifiers, seed)
    battle.start_next_wave()
    while battle.phase in ("wave", "between_waves") and battle.time < max_seconds:
        if battle.phase == "between_waves":
            battle.start_next_wave()
        battle.step(dt)
    return battle
