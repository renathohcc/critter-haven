from critter_haven.config.window_states import (
    COMPACT,
    EXPANDED,
    MEDIUM,
    state_for_height,
)


def test_compact_range():
    assert state_for_height(90).name == COMPACT.name
    assert state_for_height(120).name == COMPACT.name


def test_medium_range():
    assert state_for_height(180).name == MEDIUM.name


def test_expanded_range():
    assert state_for_height(400).name == EXPANDED.name
    assert state_for_height(900).name == EXPANDED.name
