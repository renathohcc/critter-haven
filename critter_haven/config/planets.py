"""Destinos da nave. Fase 11: um planeta é liberado quando o jogador vence
a defesa (todas as waves + chefe) do planeta anterior da cadeia -- não há
mais item de viagem."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanetDestination:
    id: str
    name: str
    theme: str
    active: bool
    unlock_after: str | None = None  # id do planeta cuja defesa precisa ser vencida


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
        unlock_after="elyndor",
    ),
    PlanetDestination(
        id="aerthos",
        name="Aerthos",
        theme="Planeta de nuvens",
        active=False,
        unlock_after="calyra",
    ),
    PlanetDestination(
        id="glacivar",
        name="Glacivar",
        theme="Gelo e vulcões",
        active=False,
        unlock_after="aerthos",
    ),
)
PLANETS_BY_ID = {p.id: p for p in PLANETS}
