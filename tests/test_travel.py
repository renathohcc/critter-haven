from critter_haven.config.planets import PLANETS
from critter_haven.economy.chest import Chest
from critter_haven.systems.travel_system import can_travel, travel


def get_planet(planet_id: str):
    return next(p for p in PLANETS if p.id == planet_id)


def test_elyndor_always_available():
    chest = Chest()
    assert can_travel(get_planet("elyndor"), chest) is True


def test_calyra_blocked_without_nucleo_solar():
    chest = Chest()
    assert can_travel(get_planet("calyra"), chest) is False


def test_calyra_unlocked_with_enough_item():
    chest = Chest()
    chest.add_item("Núcleo Solar", 1)
    assert can_travel(get_planet("calyra"), chest) is True


def test_travel_consumes_required_item():
    chest = Chest()
    chest.add_item("Núcleo Solar", 1)
    assert travel(get_planet("calyra"), chest) is True
    assert chest.items.get("Núcleo Solar", 0) == 0


def test_travel_fails_and_does_not_consume_when_missing_item():
    chest = Chest()
    assert travel(get_planet("calyra"), chest) is False
    assert chest.total_count() == 0


def test_pending_requirement_planets_are_always_blocked():
    chest = Chest()
    chest.add_item("qualquer coisa", 999)
    assert can_travel(get_planet("aerthos"), chest) is False
    assert can_travel(get_planet("glacivar"), chest) is False
