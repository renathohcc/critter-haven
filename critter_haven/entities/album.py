"""Diário de Bordo de Homie: registra a primeira descoberta de cada
espécie (GDD seção 11). Puro Python, sem dependência de Pygame/Tkinter."""

from __future__ import annotations

from dataclasses import dataclass, field

from critter_haven.data.species import Species


@dataclass
class Album:
    discovered_ids: set[str] = field(default_factory=set)

    def register(self, species: Species) -> bool:
        """Retorna True se essa foi a primeira descoberta da espécie."""
        if species.id in self.discovered_ids:
            return False
        self.discovered_ids.add(species.id)
        return True

    def is_discovered(self, species: Species) -> bool:
        return species.id in self.discovered_ids

    def progress(self, species_pool: list[Species]) -> tuple[int, int]:
        total = len(species_pool)
        discovered = sum(1 for s in species_pool if self.is_discovered(s))
        return discovered, total
