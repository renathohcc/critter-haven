from critter_haven.data.combat import PlanetDefense, SpawnGroup, load_combat_data
from critter_haven.data.species import load_planet
from critter_haven.entities.combatants import RunModifiers
from critter_haven.systems.combat_system import FIELD_LENGTH, Battle, run_battle


def make_defense(groups_per_wave, ship_hp=400.0, ship_damage=0.0) -> PlanetDefense:
    waves = tuple(
        tuple(SpawnGroup(enemy_id=e, count=c, interval=1.0, delay=0.0) for e, c in groups)
        for groups in groups_per_wave
    )
    return PlanetDefense(
        planet_id="teste",
        ship_max_hp=ship_hp,
        ship_damage=ship_damage,
        ship_range=150.0,
        ship_attack_interval=1.5,
        waves=waves,
    )


def run_until(battle: Battle, predicate, max_steps=20000, dt=0.1):
    for _ in range(max_steps):
        if predicate(battle):
            return True
        battle.step(dt)
    return predicate(battle)


def test_every_species_has_combat_stats():
    species_ids = {s.id for s in load_planet("elyndor")}
    assert species_ids <= set(load_combat_data().units)


def test_roles_match_the_design():
    units = load_combat_data().units
    assert units["pebblit"].role == "tank"
    assert units["mossnib"].role == "buffer"
    assert units["lumibloom"].role == "healer"
    assert units["breezel"].role == "attacker"
    assert units["solarva"].role == "attacker"


def test_defense_is_won_and_then_stays_won():
    battle = run_battle("elyndor", ["solarva"] * 4 + ["pebblit"] * 3 + ["lumibloom"] * 2)
    assert battle.phase == "won"
    assert battle.ship.alive


def test_defense_without_army_is_lost():
    battle = run_battle("elyndor", [])
    assert battle.phase == "lost"


def test_battle_is_deterministic_for_a_seed():
    army = ["mossnib", "pebblit", "breezel", "lumibloom"]
    a = run_battle("elyndor", army, seed=3)
    b = run_battle("elyndor", army, seed=3)
    assert (a.phase, a.wave_index, round(a.ship.hp, 6)) == (b.phase, b.wave_index, round(b.ship.hp, 6))


def test_enemies_spawn_at_the_far_end_and_walk_toward_the_ship():
    battle = Battle(make_defense([[("grunt", 1)]]), [])
    battle.start_next_wave()
    battle.step(0.1)
    assert battle.enemies and battle.enemies[0].x <= FIELD_LENGTH
    x0 = battle.enemies[0].x
    battle.step(1.0)
    assert battle.enemies[0].x < x0


def test_tank_taunt_draws_attacks_away_from_the_healer():
    battle = Battle(make_defense([[("grunt", 1)]], ship_damage=0.0), ["pebblit", "lumibloom"])
    battle.start_next_wave()
    run_until(battle, lambda b: b.phase != "wave", max_steps=3000)
    assert battle.phase == "won"
    healer = next(u for u in battle.units if u.role == "healer")
    tank = next(u for u in battle.units if u.role == "tank")
    assert healer.hp == healer.max_hp  # tudo foi absorvido pelo tanque
    assert tank.hp <= tank.max_hp


def test_buffer_aura_increases_damage_of_nearby_allies():
    battle = Battle(make_defense([[("grunt", 1)]]), ["mossnib", "breezel"])
    aura = battle._damage_aura_bonus()
    breezel = next(u for u in battle.units if u.role == "attacker")
    assert aura[breezel.uid] == load_combat_data().units["mossnib"].ability["bonus"]


def test_healer_heals_the_most_hurt_ally_in_range():
    battle = Battle(make_defense([[("grunt", 1)]]), ["pebblit", "lumibloom"])
    battle.start_next_wave()
    tank = next(u for u in battle.units if u.role == "tank")
    healer = next(u for u in battle.units if u.role == "healer")
    tank.x = healer.x + 20  # dentro do alcance de cura
    tank.hp = tank.max_hp * 0.4
    battle.step(0.1)
    assert tank.hp > tank.max_hp * 0.4


def test_slow_hit_slows_the_target():
    battle = Battle(make_defense([[("brute", 1)]]), ["breezel"])
    battle.start_next_wave()
    breezel = battle.units[0]
    battle.step(0.1)
    enemy = battle.enemies[0]
    enemy.x = breezel.x + 10
    breezel.cooldown = 0.0
    battle.step(0.1)
    assert enemy.slow_factor < 1.0


def test_splash_damages_enemies_next_to_the_target():
    battle = Battle(make_defense([[("brute", 2)]]), ["solarva"])
    battle.start_next_wave()
    solarva = battle.units[0]
    battle.step(1.0)
    battle.step(1.0)
    first, second = battle.enemies[0], battle.enemies[1]
    first.x = second.x = solarva.x + 50
    solarva.cooldown = 0.0
    before = second.hp
    battle.step(0.1)
    assert second.hp < before


def test_ship_destroyed_loses_the_battle():
    battle = Battle(make_defense([[("brute", 6)]], ship_hp=30.0), [])
    battle.start_next_wave()
    run_until(battle, lambda b: b.phase != "wave", max_steps=20000)
    assert battle.phase == "lost"


def test_fallen_units_revive_between_waves_and_survivors_heal():
    battle = Battle(make_defense([[("grunt", 1)], [("grunt", 1)]], ship_damage=50.0), ["pebblit"])
    battle.start_next_wave()
    unit = battle.units[0]
    unit.hp = 0.0
    run_until(battle, lambda b: b.phase == "between_waves", max_steps=20000)
    assert battle.phase == "between_waves"
    assert unit.alive and unit.hp > 0


def test_modifiers_scale_unit_hp():
    base = Battle(make_defense([[("grunt", 1)]]), ["pebblit"])
    buffed = Battle(make_defense([[("grunt", 1)]]), ["pebblit"], RunModifiers(unit_hp=1.5))
    assert buffed.units[0].max_hp == base.units[0].max_hp * 1.5


def test_start_next_wave_is_ignored_while_a_wave_is_running():
    battle = Battle(make_defense([[("grunt", 1)], [("grunt", 1)]]), [])
    battle.start_next_wave()
    battle.start_next_wave()
    assert battle.wave_index == 0
