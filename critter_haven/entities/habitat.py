"""Habitat: contém as criaturas ativas e acumula energia para spawn."""

from __future__ import annotations

from dataclasses import dataclass, field

from critter_haven.config.habitat_zones import SPECIES_ROAM_FRACTIONS
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
    energy_per_second: float = ENERGY_PER_SECOND
    max_creatures: int = BASE_MAX_CREATURES
    creatures: list[Creature] = field(default_factory=list)
    last_spawn_species: Species | None = None

    def update(self, dt: float) -> Species | None:
        self.energy = min(ENERGY_MAX, self.energy + self.energy_per_second * dt)
        spawned = None
        # Se o habitat estiver cheio, a energia fica represada no máximo em
        # vez de se perder — assim que houver espaço, o spawn acontece na
        # próxima atualização, sem desperdiçar o tempo de espera do jogador.
        if self.energy >= ENERGY_MAX and not self.is_full:
            spawned = self.spawn_one()
            self.energy = 0.0
        for creature in self.creatures:
            creature.update(dt, self.min_x, self.max_x)
        return spawned

    @property
    def is_full(self) -> bool:
        return len(self.creatures) >= self.max_creatures

    def spawn_one(self) -> Species:
        """Spawna uma criatura imediatamente (usado pelo update normal e
        pelo cálculo de progresso offline, que simula spawns represados)."""
        return self._spawn()

    def _roam_bounds_for(self, species_id: str) -> tuple[float, float]:
        fractions = SPECIES_ROAM_FRACTIONS.get(species_id)
        if fractions is None:
            return self.min_x, self.max_x
        frac_min, frac_max = fractions
        span = self.max_x - self.min_x
        return self.min_x + span * frac_min, self.min_x + span * frac_max

    def _spawn(self) -> Species:
        species = roll_species(self.species_pool)
        roam_min, roam_max = self._roam_bounds_for(species.id)
        x = (roam_min + roam_max) / 2
        self.creatures.append(
            Creature(
                species=species,
                x=x,
                y=self.spawn_y,
                roam_min_x=roam_min,
                roam_max_x=roam_max,
            )
        )
        self.last_spawn_species = species
        return species

    def resync_roam_bounds(self) -> None:
        """Recalcula as zonas de circulação de todas as criaturas — chamar
        depois de mudar habitat.min_x/max_x (ex: redimensionar a janela),
        já que as zonas são frações da largura útil do habitat."""
        for creature in self.creatures:
            roam_min, roam_max = self._roam_bounds_for(creature.species.id)
            creature.roam_min_x, creature.roam_max_x = roam_min, roam_max
            creature.x = min(max(creature.x, roam_min), roam_max)

    def energy_ratio(self) -> float:
        return self.energy / ENERGY_MAX

    def creature_at(self, x: float, y: float, radius: float = 28.0) -> Creature | None:
        for creature in reversed(self.creatures):
            if (creature.x - x) ** 2 + (creature.y - y) ** 2 <= radius**2:
                return creature
        return None

    def count_of(self, species_id: str) -> int:
        return sum(1 for c in self.creatures if c.species.id == species_id)

    def has_duplicate(self, species_id: str) -> bool:
        return self.count_of(species_id) >= 2

    def release_duplicate(self, species_id: str) -> bool:
        """Remove uma criatura duplicada (mantendo ao menos uma da espécie)
        para abrir espaço no habitat. Retorna False se não há duplicata."""
        if not self.has_duplicate(species_id):
            return False
        for i, creature in enumerate(self.creatures):
            if creature.species.id == species_id:
                del self.creatures[i]
                return True
        return False

    def sacrifice_duplicate_and_spawn(self, species_id: str) -> Species | None:
        """Usa uma criatura duplicada como recurso: libera espaço e sorteia
        uma nova criatura na hora, sem esperar a energia encher.

        Resolve o problema de descoberta travada pela capacidade do habitat
        — decisão de balanceamento tomada com o dev (Fase 8): em vez de
        aumentar infinitamente a capacidade, duplicatas viram um recurso
        de progressão que o jogador já acumula naturalmente jogando.
        """
        if not self.release_duplicate(species_id):
            return None
        return self.spawn_one()
