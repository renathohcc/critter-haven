from critter_haven.config.upgrades import GOLD_PRODUCTION, OFFLINE_PROGRESS
from critter_haven.economy.upgrades import UpgradeManager
from critter_haven.economy.wallet import Wallet


def test_cost_grows_exponentially_per_level():
    manager = UpgradeManager()
    first_cost = manager.cost(GOLD_PRODUCTION)
    assert first_cost == GOLD_PRODUCTION.base_cost

    manager.levels[GOLD_PRODUCTION.id] = 1
    second_cost = manager.cost(GOLD_PRODUCTION)
    assert second_cost == round(GOLD_PRODUCTION.base_cost * GOLD_PRODUCTION.cost_growth, 2)


def test_buy_fails_without_enough_gold():
    manager = UpgradeManager()
    wallet = Wallet(gold=10)
    assert manager.buy(GOLD_PRODUCTION, wallet) is False
    assert manager.level(GOLD_PRODUCTION.id) == 0


def test_buy_succeeds_and_increments_level():
    manager = UpgradeManager()
    wallet = Wallet(gold=1000)
    assert manager.buy(GOLD_PRODUCTION, wallet) is True
    assert manager.level(GOLD_PRODUCTION.id) == 1
    assert wallet.gold == 1000 - GOLD_PRODUCTION.base_cost


def test_effect_total_scales_with_level():
    manager = UpgradeManager()
    manager.levels[GOLD_PRODUCTION.id] = 3
    assert manager.effect_total(GOLD_PRODUCTION) == 3 * GOLD_PRODUCTION.effect_per_level


def test_cannot_buy_past_max_level():
    manager = UpgradeManager()
    manager.levels[GOLD_PRODUCTION.id] = GOLD_PRODUCTION.max_level
    wallet = Wallet(gold=10**9)
    assert manager.cost(GOLD_PRODUCTION) is None
    assert manager.buy(GOLD_PRODUCTION, wallet) is False


def test_offline_progress_starts_locked_at_zero_hours():
    manager = UpgradeManager()
    assert manager.effect_total(OFFLINE_PROGRESS) == 0


def test_offline_progress_grants_one_hour_per_level_up_to_four():
    manager = UpgradeManager()
    wallet = Wallet(gold=10**9)
    for expected_hours in (1, 2, 3, 4):
        manager.buy(OFFLINE_PROGRESS, wallet)
        assert manager.effect_total(OFFLINE_PROGRESS) == expected_hours * 3600
    assert manager.buy(OFFLINE_PROGRESS, wallet) is False  # nivel maximo (4h)
