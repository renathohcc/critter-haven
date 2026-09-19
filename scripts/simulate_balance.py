"""Simulação headless de balanceamento (GDD seção 12).

Roda o loop econômico puro (sem Pygame) com um "jogador" heurístico que
vende o baú sempre que está cheio e compra o upgrade mais barato que
consegue pagar sempre que tem ouro sobrando. Mede métricas de
progressão para validar a curva antes de fixá-la como definitiva.

Uso: python scripts/simulate_balance.py [horas]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from critter_haven.config.upgrades import UPGRADES
from critter_haven.data.species import load_planet
from critter_haven.economy.chest import Chest
from critter_haven.economy.pricing import build_price_map, sell_all
from critter_haven.economy.upgrades import UpgradeManager
from critter_haven.economy.wallet import Wallet
from critter_haven.entities.album import Album
from critter_haven.entities.habitat import Habitat
from critter_haven.systems.production_system import update_production

DT = 1.0  # segundos por passo de simulação


def run_simulation(hours: float) -> dict:
    species_pool = load_planet("elyndor")
    habitat = Habitat(planet="elyndor", species_pool=species_pool, max_x=780)
    wallet = Wallet()
    chest = Chest()
    album = Album()
    upgrades = UpgradeManager()
    price_map = build_price_map(species_pool)

    total_seconds = int(hours * 3600)
    milestones: dict[str, float] = {}
    upgrade_purchases: list[tuple[float, str, int]] = []
    gold_curve: list[tuple[float, float]] = []

    for second in range(total_seconds):
        spawned = habitat.update(DT)
        if spawned:
            was_new = album.register(spawned)
            if was_new and f"first_{spawned.id}" not in milestones:
                milestones[f"first_{spawned.id}"] = second

        gold_multiplier = 1.0 + upgrades.effect_total(
            next(u for u in UPGRADES if u.id == "gold_production")
        )
        update_production(habitat.creatures, DT, wallet, chest, gold_multiplier)

        if chest.is_full:
            sell_all(chest, wallet, price_map)

        # jogador heurístico: compra o upgrade mais barato que pode pagar
        affordable = [
            (upgrades.cost(u), u)
            for u in UPGRADES
            if upgrades.cost(u) is not None and wallet.can_afford(upgrades.cost(u))
        ]
        if affordable:
            cost, cheapest = min(affordable, key=lambda pair: pair[0])
            if upgrades.buy(cheapest, wallet):
                upgrade_purchases.append((second, cheapest.id, upgrades.level(cheapest.id)))
                if f"first_upgrade" not in milestones:
                    milestones["first_upgrade"] = second

        if habitat.is_full and "habitat_full" not in milestones:
            milestones["habitat_full"] = second

        # jogador heurístico: usa duplicatas como recurso pra continuar
        # descobrindo espécies novas em vez de deixar o habitat travado
        discovered, total = album.progress(species_pool)
        if discovered < total:
            for species in species_pool:
                if habitat.has_duplicate(species.id):
                    spawned = habitat.sacrifice_duplicate_and_spawn(species.id)
                    if spawned:
                        was_new = album.register(spawned)
                        if was_new and f"first_{spawned.id}" not in milestones:
                            milestones[f"first_{spawned.id}"] = second
                    break

        if album.progress(species_pool) == (len(species_pool), len(species_pool)):
            if "album_complete" not in milestones:
                milestones["album_complete"] = second

        if second % 300 == 0:  # amostra a cada 5 min simulados
            gold_curve.append((second, wallet.gold))

    return {
        "hours_simulated": hours,
        "final_gold": wallet.gold,
        "milestones": milestones,
        "upgrade_purchases": upgrade_purchases,
        "gold_curve": gold_curve,
        "album_discovered": album.progress(species_pool),
        "upgrade_levels": dict(upgrades.levels),
    }


def format_seconds(s: float) -> str:
    minutes = s / 60
    if minutes < 60:
        return f"{minutes:.1f} min"
    return f"{minutes / 60:.2f} h"


def report(result: dict) -> None:
    print(f"=== Simulação: {result['hours_simulated']}h ===")
    print(f"Ouro final: {result['final_gold']:.0f}")
    print(f"Álbum: {result['album_discovered'][0]}/{result['album_discovered'][1]}")
    print(f"Upgrades comprados: {len(result['upgrade_purchases'])}")
    print(f"Níveis finais: {result['upgrade_levels']}")
    print("\nMarcos (tempo até acontecer):")
    for key in [
        "first_upgrade",
        "habitat_full",
        "first_breezel",
        "first_solarva",
        "album_complete",
    ]:
        seconds = result["milestones"].get(key)
        label = format_seconds(seconds) if seconds is not None else "não atingido"
        print(f"  {key}: {label}")
    print("\nCurva de ouro (amostras a cada 5 min):")
    for second, gold in result["gold_curve"][:12]:
        print(f"  {format_seconds(second):>8}: {gold:.0f} ouro")


if __name__ == "__main__":
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    result = run_simulation(hours)
    report(result)
