import random

from critter_haven.data.combat import load_combat_data
from critter_haven.systems.cards import (
    CHOICES_PER_WAVE,
    apply_card,
    card_by_id,
    draw_choices,
    load_cards,
    run_battle_with_cards,
)
from critter_haven.systems.combat_system import Battle


def make_battle(army=("pebblit", "breezel")) -> Battle:
    return Battle(load_combat_data().planets["elyndor"], list(army))


def test_all_cards_have_known_effect_types():
    known = {"mod", "role_mod", "ship_hp_bonus", "heal_ship", "heal_units"}
    for card in load_cards():
        assert card.effects and all(e["type"] in known for e in card.effects)


def test_draw_returns_three_distinct_cards():
    choices = draw_choices(random.Random(1))
    assert len(choices) == CHOICES_PER_WAVE
    assert len({c.card_id for c in choices}) == CHOICES_PER_WAVE


def test_draw_skips_cards_already_taken():
    taken = [c.card_id for c in load_cards()[:-3]]
    for seed in range(20):
        ids = {c.card_id for c in draw_choices(random.Random(seed), taken)}
        assert ids.isdisjoint(taken)


def test_draw_is_deterministic_for_a_seed():
    a = [c.card_id for c in draw_choices(random.Random(7))]
    b = [c.card_id for c in draw_choices(random.Random(7))]
    assert a == b


def test_global_multiplier_card_changes_modifier():
    battle = make_battle()
    apply_card(battle, card_by_id("garras_afiadas"))
    assert battle.modifiers.unit_damage == 1.15


def test_hp_card_scales_max_and_current_hp_proportionally():
    battle = make_battle()
    unit = battle.units[0]
    unit.hp = unit.max_hp / 2
    base_max = unit.max_hp
    apply_card(battle, card_by_id("casca_dura"))
    assert unit.max_hp == base_max * 1.2
    assert round(unit.hp / unit.max_hp, 6) == 0.5


def test_role_card_only_affects_that_role():
    battle = make_battle()
    tank = next(u for u in battle.units if u.role == "tank")
    attacker = next(u for u in battle.units if u.role == "attacker")
    t_max, a_max = tank.max_hp, attacker.max_hp
    apply_card(battle, card_by_id("muralha_viva"))
    assert tank.max_hp == t_max * 1.4 and attacker.max_hp == a_max


def test_ship_cards_heal_and_raise_max_hp():
    battle = make_battle()
    battle.ship.hp = 100
    apply_card(battle, card_by_id("reparos_de_emergencia"))
    assert battle.ship.hp == 100 + battle.ship.max_hp * 0.4
    before = battle.ship.max_hp
    apply_card(battle, card_by_id("reforco_do_casco"))
    assert battle.ship.max_hp == before + 100


def test_run_with_cards_picks_one_card_per_wave_between_waves():
    battle, picked = run_battle_with_cards("elyndor", ["pebblit", "breezel", "solarva"] * 3, seed=1)
    assert len(picked) == max(0, battle.wave_index if battle.phase == "won" else battle.wave_index)
    assert len(set(picked)) == len(picked)
