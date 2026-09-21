"""Zonas de circulação por espécie dentro do habitat, como fração da
largura útil do habitat (0.0-1.0) — pensadas pra combinar a posição da
criatura com pontos de interesse do cenário desenhado no Tiled (ex:
Mossnib fica perto do salgueiro, à esquerda do mapa de Elyndor).

Espécies fora deste dicionário circulam pelo habitat inteiro (padrão
anterior a essa feature)."""

SPECIES_ROAM_FRACTIONS: dict[str, tuple[float, float]] = {
    # Elyndor.tmx tem 30 colunas de 32px (960px). "Colunas 1-10" do mapa
    # (pedido do dev, região do salgueiro) = pixels 0-320 = fração 0-0.333.
    "mossnib": (0.0, 0.3333),
}

# Espécies que nascem numa posição e ficam fixas ali pra sempre (ex: uma
# flor não anda). Cada indivíduo sorteia sua própria posição dentro da
# zona da espécie (ou do habitat inteiro, se não tiver zona definida) e
# fica pinado lá — não é uma zona compartilhada como SPECIES_ROAM_FRACTIONS.
STATIONARY_SPECIES: set[str] = {"lumibloom"}
