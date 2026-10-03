from critter_haven.config.planets import PLANETS
from critter_haven.systems.travel_system import can_travel, travel


def get_planet(planet_id: str):
    return next(p for p in PLANETS if p.id == planet_id)


def test_elyndor_always_available():
    assert can_travel(get_planet("elyndor"), set()) is True


def test_calyra_blocked_until_elyndor_defense_is_cleared():
    assert can_travel(get_planet("calyra"), set()) is False
    assert can_travel(get_planet("calyra"), {"elyndor"}) is True


def test_travel_succeeds_only_when_unlocked():
    assert travel(get_planet("calyra"), set()) is False
    assert travel(get_planet("calyra"), {"elyndor"}) is True


def test_chain_requires_each_previous_planet():
    assert can_travel(get_planet("aerthos"), {"elyndor"}) is False
    assert can_travel(get_planet("aerthos"), {"elyndor", "calyra"}) is True
    assert can_travel(get_planet("glacivar"), {"calyra"}) is False
    assert can_travel(get_planet("glacivar"), {"aerthos"}) is True
