from critter_haven.data.species import load_planet
from critter_haven.economy.chest import Chest
from critter_haven.economy.pricing import build_price_map, sell_all
from critter_haven.economy.wallet import Wallet
from critter_haven.entities.creature import Creature
from critter_haven.systems.production_system import update_production


def get_species(species_id: str):
    return next(s for s in load_planet("elyndor") if s.id == species_id)


def test_wallet_add_and_spend():
    wallet = Wallet()
    wallet.add(100)
    assert wallet.gold == 100
    assert wallet.spend(40) is True
    assert wallet.gold == 60
    assert wallet.spend(1000) is False
    assert wallet.gold == 60


def test_chest_add_respects_capacity():
    chest = Chest(capacity=2)
    assert chest.add_item("Folha Viva") is True
    assert chest.add_item("Folha Viva") is True
    assert chest.is_full
    assert chest.add_item("Folha Viva") is False
    assert chest.total_count() == 2


def test_chest_clear_returns_previous_items():
    chest = Chest()
    chest.add_item("Pedra Polida", 3)
    removed = chest.clear()
    assert removed == {"Pedra Polida": 3}
    assert chest.total_count() == 0


def test_production_adds_gold_over_time():
    mossnib = get_species("mossnib")
    creature = Creature(species=mossnib, x=0, y=0)
    wallet = Wallet()
    chest = Chest()

    update_production([creature], 1.0, wallet, chest)
    assert wallet.gold == mossnib.base_gold_per_second


def test_production_drops_item_after_interval():
    mossnib = get_species("mossnib")  # comum -> intervalo de 8s
    creature = Creature(species=mossnib, x=0, y=0)
    wallet = Wallet()
    chest = Chest()

    update_production([creature], 7.9, wallet, chest)
    assert chest.total_count() == 0

    update_production([creature], 0.2, wallet, chest)
    assert chest.items.get("Folha Viva") == 1


def test_sell_all_converts_items_to_gold_and_clears_chest():
    species_list = load_planet("elyndor")
    price_map = build_price_map(species_list)
    chest = Chest()
    chest.add_item("Folha Viva", 2)
    wallet = Wallet()

    total = sell_all(chest, wallet, price_map)

    assert total == price_map["Folha Viva"] * 2
    assert wallet.gold == total
    assert chest.total_count() == 0


def test_sell_all_with_empty_chest_is_noop():
    chest = Chest()
    wallet = Wallet()
    total = sell_all(chest, wallet, {})
    assert total == 0
    assert wallet.gold == 0
