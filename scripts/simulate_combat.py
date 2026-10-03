"""Simulação headless da defesa (Fase 11): roda várias batalhas com
exércitos de referência e reporta taxa de vitória e em que wave cai.

Uso: python scripts/simulate_combat.py [planeta] [sementes]
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from critter_haven.systems.cards import run_battle_with_cards
from critter_haven.systems.combat_system import run_battle

ARMIES = {
    "inicial (6 criaturas)": ["mossnib", "pebblit", "lumibloom", "mossnib", "pebblit", "lumibloom"],
    "medio (10 criaturas)": [
        "mossnib", "pebblit", "lumibloom", "mossnib", "pebblit",
        "lumibloom", "breezel", "breezel", "mossnib", "pebblit",
    ],
    "medio-forte (13 criaturas)": [
        "mossnib", "pebblit", "lumibloom", "mossnib", "pebblit", "lumibloom",
        "breezel", "breezel", "solarva", "mossnib", "pebblit", "lumibloom", "breezel",
    ],
    "forte (16 criaturas)": [
        "mossnib", "pebblit", "lumibloom", "mossnib", "pebblit", "lumibloom",
        "breezel", "breezel", "solarva", "mossnib", "pebblit", "lumibloom",
        "breezel", "solarva", "pebblit", "lumibloom",
    ],
}


def main() -> None:
    planet = sys.argv[1] if len(sys.argv) > 1 else "elyndor"
    seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    for name, army in ARMIES.items():
        wins = 0
        lost_at: Counter = Counter()
        ship_left = []
        durations = []
        for seed in range(seeds):
            battle = run_battle(planet, army, seed=seed)
            durations.append(battle.time)
            if battle.phase == "won":
                wins += 1
                ship_left.append(battle.ship.hp / battle.ship.max_hp)
            else:
                lost_at[battle.wave_index + 1] += 1
        card_wins = 0
        card_wave = []
        for seed in range(seeds):
            battle, _picked = run_battle_with_cards(planet, army, seed=seed)
            card_wins += battle.phase == "won"
            card_wave.append(battle.wave_index + 1)
        avg_ship = sum(ship_left) / len(ship_left) if ship_left else 0.0
        print(
            f"{name}: vitorias {wins}/{seeds} | nave restante (vit.) {avg_ship:.0%} | "
            f"duracao media {sum(durations) / len(durations) / 60:.1f} min | "
            f"caiu na wave: {dict(sorted(lost_at.items()))}"
        )
        print(
            f"    com cartas aleatorias: vitorias {card_wins}/{seeds} | "
            f"wave media alcancada {sum(card_wave) / len(card_wave):.1f}"
        )


if __name__ == "__main__":
    main()
