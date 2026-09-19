from critter_haven.data.species import load_planet
from critter_haven.entities.creature import (
    REST_DURATION_RANGE,
    WALK_DURATION_RANGE,
    Creature,
)


def get_species(species_id: str):
    return next(s for s in load_planet("elyndor") if s.id == species_id)


def test_creature_starts_resting():
    creature = Creature(species=get_species("mossnib"), x=100, y=0)
    assert creature.state == "resting"
    assert not creature.is_walking


def test_creature_does_not_move_while_resting():
    creature = Creature(species=get_species("mossnib"), x=100, y=0)
    creature.state_timer = 10.0  # garante que nao transiciona nesse update
    creature.update(dt=0.5, min_x=0, max_x=800)
    assert creature.x == 100


def test_creature_switches_to_walking_after_resting_expires():
    creature = Creature(species=get_species("mossnib"), x=100, y=0)
    creature.state_timer = 0.01
    creature.update(dt=0.5, min_x=0, max_x=800)
    assert creature.is_walking
    assert WALK_DURATION_RANGE[0] <= creature.state_timer <= WALK_DURATION_RANGE[1] + 0.5


def test_creature_moves_while_walking():
    creature = Creature(species=get_species("mossnib"), x=100, y=0, state="walking")
    creature.state_timer = 5.0
    creature.direction = 1
    creature.update(dt=0.5, min_x=0, max_x=800)
    assert creature.x > 100


def test_creature_returns_to_resting_after_walk_expires():
    creature = Creature(species=get_species("mossnib"), x=100, y=0, state="walking")
    creature.state_timer = 0.01
    creature.update(dt=0.5, min_x=0, max_x=800)
    assert creature.state == "resting"
    assert REST_DURATION_RANGE[0] <= creature.state_timer <= REST_DURATION_RANGE[1] + 0.5
