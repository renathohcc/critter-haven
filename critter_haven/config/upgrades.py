"""Definições dos upgrades (GDD 6.6). Quantidade e curva de custo definidas
em conversa com o dev — ajustáveis aqui sem tocar no sistema."""

from dataclasses import dataclass

COST_GROWTH = 1.15


@dataclass(frozen=True)
class UpgradeDef:
    id: str
    name: str
    description: str
    base_cost: float
    effect_per_level: float
    max_level: int
    cost_growth: float = COST_GROWTH


GOLD_PRODUCTION = UpgradeDef(
    id="gold_production",
    name="Produção de Ouro",
    description="+10% de ouro/s em todas as criaturas por nível",
    base_cost=50,
    effect_per_level=0.10,
    max_level=20,
)

SPAWN_SPEED = UpgradeDef(
    id="spawn_speed",
    name="Velocidade de Spawn",
    description="+0.15 energia/s por nível (spawn mais rápido)",
    base_cost=80,
    effect_per_level=0.15,
    max_level=15,
)

HABITAT_CAPACITY = UpgradeDef(
    id="habitat_capacity",
    name="Capacidade do Habitat",
    description="+1 criatura simultânea por nível",
    base_cost=150,
    effect_per_level=1,
    max_level=10,
)

CHEST_CAPACITY = UpgradeDef(
    id="chest_capacity",
    name="Capacidade do Baú",
    description="+25 de espaço de itens por nível",
    base_cost=100,
    effect_per_level=25,
    max_level=10,
)

UPGRADES = (GOLD_PRODUCTION, SPAWN_SPEED, HABITAT_CAPACITY, CHEST_CAPACITY)
UPGRADES_BY_ID = {u.id: u for u in UPGRADES}
