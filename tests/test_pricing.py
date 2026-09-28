from critter_haven.economy.chest import Chest
from critter_haven.economy.pricing import sell_item
from critter_haven.economy.wallet import Wallet


def make_chest_with(item_name: str, quantity: int) -> Chest:
    chest = Chest()
    chest.items[item_name] = quantity
    return chest


def test_sell_item_sells_only_the_requested_quantity():
    chest = make_chest_with("Folha Viva", 10)
    wallet = Wallet()
    price_map = {"Folha Viva": 2.0}

    total = sell_item(chest, wallet, price_map, "Folha Viva", 3)

    assert total == 6.0
    assert wallet.gold == 6.0
    assert chest.items["Folha Viva"] == 7


def test_sell_item_removes_the_entry_when_fully_sold():
    chest = make_chest_with("Pedra Polida", 5)
    wallet = Wallet()
    price_map = {"Pedra Polida": 1.5}

    sell_item(chest, wallet, price_map, "Pedra Polida", 5)

    assert "Pedra Polida" not in chest.items


def test_sell_item_clamps_to_available_quantity():
    chest = make_chest_with("Nucleo Solar", 2)
    wallet = Wallet()
    price_map = {"Nucleo Solar": 10.0}

    total = sell_item(chest, wallet, price_map, "Nucleo Solar", 99)

    assert total == 20.0
    assert "Nucleo Solar" not in chest.items


def test_sell_item_does_nothing_for_missing_item():
    chest = Chest()
    wallet = Wallet()

    total = sell_item(chest, wallet, {}, "Inexistente", 1)

    assert total == 0.0
    assert wallet.gold == 0.0
