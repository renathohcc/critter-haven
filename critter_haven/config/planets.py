"""Destinos da nave (GDD seção 6/7). Aerthos e Glacivar têm requisito
'a definir' no próprio GDD — usamos placeholder configurável em vez de
inventar um valor definitivo (decisão registrada com o dev)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanetDestination:
    id: str
    name: str
    theme: str
    active: bool
    required_item: str | None = None
    required_quantity: int = 0
    requirement_pending: bool = False


PLANETS = (
    PlanetDestination(
        id="elyndor",
        name="Elyndor",
        theme="Terra natal — verde e próspera",
        active=True,
    ),
    PlanetDestination(
        id="calyra",
        name="Calyra",
        theme="Deserto árido",
        active=False,
        required_item="Núcleo Solar",
        required_quantity=1,
    ),
    PlanetDestination(
        id="aerthos",
        name="Aerthos",
        theme="Planeta de nuvens",
        active=False,
        requirement_pending=True,
    ),
    PlanetDestination(
        id="glacivar",
        name="Glacivar",
        theme="Gelo e vulcões",
        active=False,
        requirement_pending=True,
    ),
)
