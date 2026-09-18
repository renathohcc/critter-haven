"""Habitat: contém as criaturas ativas e acumula energia para spawn."""

from __future__ import annotations

from dataclasses import dataclass, field

from critter_haven.config.spawn import (
    BASE_MAX_CREATURES,
    ENERGY_MAX,
    ENERGY_PER_SECOND,
)
from critter_haven.entities.creature import Creature
from critter_haven.systems.spawn_system import roll_species
from critter_haven.data.species import Species


@dataclass
class Habitat:
    planet: str
    species_pool: list[Species]
    min_x: float = 20.0
    max_x: float = 780.0
    spawn_y: float = 60.0
    energy: float = 0.0
    max_creatures: int = BASE_MAX_CREATURES
    creatures: list[Creature] = field(default_factory=list)
    last_spawn_species: Species | None = None

    def update(self, dt: float) -> Species | None:
        self.energy = min(ENERGY_MAX, self.energy + ENERGY_PER_SECOND * dt)
        spawned = None
        # Se o habitat estiver cheio, a energia fica represada no máximo em
        # vez de se perder — assim que houver espaço, o spawn acontece na
        # próxima atualização, sem desperdiçar o tempo de espera do jogador.
        if self.energy >= ENERGY_MAX and not self.is_full:
            spawned = self._spawn()
            self.energy = 0.0
        for creature in self.creatures:
            creature.update(dt, self.min_x, self.max_x)
        return spawned

    @property
    def is_full(self) -> bool:
        return len(self.creatures) >= self.max_creatures

    def _spawn(self) -> Species:
        species = roll_species(self.species_pool)
        x = (self.min_x + self.max_x) / 2
        self.creatures.append(Creature(species=species, x=x, y=self.spawn_y))
        self.last_spawn_species = species
        return species

    def energy_ratio(self) -> float:
        return self.energy / ENERGY_MAX

    def creature_at(self, x: float, y: float, radius: float = 24.0) -> Creature | None:
        for creature in reversed(self.creatures):
            if (creature.x - x) ** 2 + (creature.y - y) ** 2 <= radius**2:
                return creature
        return None
