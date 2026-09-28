"""Habitat: contém as criaturas ativas e acumula energia para spawn."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from critter_haven.config.habitat_zones import SPECIES_ROAM_FRACTIONS, STATIONARY_SPECIES
from critter_haven.config.spawn import (
    BASE_MAX_CREATURES,
    ENERGY_MAX,
    ENERGY_PER_SECOND,
)
from critter_haven.entities.creature import Creature
from critter_haven.systems.spawn_system import roll_species, roll_species_for_fusion
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
        return self._place_creature(species)

    def _place_creature(self, species: Species) -> Species:
        roam_min, roam_max = self._roam_bounds_for(species.id)

        if species.id in STATIONARY_SPECIES:
            # planta numa posição aleatória dentro da zona e fixa ali pra
            # sempre — não é uma zona compartilhada, cada indivíduo tem a
            # sua (ex: uma flor não anda, e várias não devem nascer
            # empilhadas no mesmo x).
            x = random.uniform(roam_min, roam_max)
            roam_min = roam_max = x
        else:
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
            if creature.species.id in STATIONARY_SPECIES:
                # nao reamostra uma nova posicao aleatoria -- so garante que
                # a posicao ja fixada continua dentro dos limites (janela
                # pode ter encolhido) e mantem o pino de largura zero ali.
                creature.x = min(max(creature.x, self.min_x), self.max_x)
                creature.roam_min_x = creature.roam_max_x = creature.x
                continue
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

    def creature_by_id(self, creature_id: int) -> Creature | None:
        """Acha a criatura viva cujo `id(objeto)` é `creature_id`. Usado
        pela Fusão (Fase 8.6 revisão): a janela Tkinter só conhece um
        snapshot com ids/nomes/raridades, nunca os objetos de verdade
        (threads diferentes), então o comando de fusão chega como um par
        de ids que precisa ser resolvido de volta pra criatura aqui."""
        for creature in self.creatures:
            if id(creature) == creature_id:
                return creature
        return None

    def can_fuse(self, creature_id_a: int, creature_id_b: int) -> bool:
        if creature_id_a == creature_id_b:
            return False
        return (
            self.creature_by_id(creature_id_a) is not None
            and self.creature_by_id(creature_id_b) is not None
        )

    def fuse_creatures(self, creature_id_a: int, creature_id_b: int) -> Species | None:
        """Fusão (Fase 8.6 revisão): consome DUAS criaturas quaisquer do
        habitat — de espécies iguais ou diferentes, não precisa mais ser
        duplicata da mesma espécie — e sorteia uma nova criatura.

        A raridade sorteada depende da combinação das raridades das duas
        criaturas usadas (ver `FUSION_RARITY_WEIGHTS`): fundir duas
        criaturas raras/especiais aumenta bastante a chance do resultado
        também ser raro/especial, recompensando quem investe as melhores
        criaturas na fusão em vez de só as comuns.
        """
        if not self.can_fuse(creature_id_a, creature_id_b):
            return None
        creature_a = self.creature_by_id(creature_id_a)
        creature_b = self.creature_by_id(creature_id_b)
        rarity_a, rarity_b = creature_a.rarity, creature_b.rarity
        self.creatures.remove(creature_a)
        self.creatures.remove(creature_b)
        species = roll_species_for_fusion(self.species_pool, rarity_a, rarity_b)
        return self._place_creature(species)
