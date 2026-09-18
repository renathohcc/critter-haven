from critter_haven.config.window_states import COMPACT, EXPANDED, MEDIUM, next_state


def test_cycle_goes_compact_to_medium_to_expanded_and_back():
    assert next_state(COMPACT) == MEDIUM
    assert next_state(MEDIUM) == EXPANDED
    assert next_state(EXPANDED) == COMPACT
