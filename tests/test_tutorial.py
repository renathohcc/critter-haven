from critter_haven.systems.tutorial import ENERGY_INFO_MAX_SECONDS, Tutorial


def test_new_game_starts_at_first_step():
    t = Tutorial.new_game()
    assert t.active and t.step == "click_creature"


def test_events_advance_only_in_order():
    t = Tutorial.new_game()
    t.on_event("sold")  # fora de ordem: ignora
    assert t.step == "click_creature"
    for event, expected in [
        ("creature_clicked", "wait_item"),
        ("item_dropped", "open_chest"),
        ("chest_opened", "sell"),
        ("sold", "buy_upgrade"),
        ("upgrade_bought", "energy_info"),
        ("spawned", "done"),
    ]:
        t.on_event(event)
        assert t.step == expected
    assert not t.active


def test_last_step_expires_by_time():
    t = Tutorial(step="energy_info")
    t.tick(ENERGY_INFO_MAX_SECONDS + 1)
    assert not t.active


def test_skip_ends_tutorial():
    t = Tutorial.new_game()
    t.skip()
    assert not t.active and t.text == "" and t.highlights == ()


def test_from_saved_handles_old_or_unknown_saves():
    assert not Tutorial.from_saved(None).active
    assert not Tutorial.from_saved("lixo").active
    assert Tutorial.from_saved("sell").step == "sell"
