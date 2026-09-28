"""Gera os retratos (frame idle, ampliado) e as silhuetas ("sombra") de
cada criatura pro Álbum, a partir dos spritesheets já montados em
assets/creatures/<id>.png + <id>.json.

Roda uma vez como parte do pipeline de assets (PIL só é dependência de
scripts/, não de runtime) e escreve em:
    critter_haven/assets/creatures/portraits/<id>.png   (colorido)
    critter_haven/assets/creatures/silhouettes/<id>.png (preto, so o
                                                          contorno/alpha)

Uso:
    python scripts/generate_album_portraits.py
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CREATURES_DIR = ROOT / "critter_haven" / "assets" / "creatures"
PORTRAITS_DIR = CREATURES_DIR / "portraits"
SILHOUETTES_DIR = CREATURES_DIR / "silhouettes"


def extract_idle_frame(species_id: str) -> Image.Image:
    meta = json.loads((CREATURES_DIR / f"{species_id}.json").read_text(encoding="utf-8"))
    frame_w, frame_h = meta["frame_size"]
    idle_index = meta["states"]["idle"]["frames"][0]
    sheet = Image.open(CREATURES_DIR / f"{species_id}.png").convert("RGBA")
    box = (idle_index * frame_w, 0, idle_index * frame_w + frame_w, frame_h)
    return sheet.crop(box)


def make_silhouette(frame: Image.Image) -> Image.Image:
    silhouette = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    pixels = frame.load()
    out_pixels = silhouette.load()
    for y in range(frame.height):
        for x in range(frame.width):
            r, g, b, a = pixels[x, y]
            if a > 0:
                out_pixels[x, y] = (8, 6, 6, 255)
    return silhouette


def main() -> None:
    PORTRAITS_DIR.mkdir(parents=True, exist_ok=True)
    SILHOUETTES_DIR.mkdir(parents=True, exist_ok=True)

    species_ids = sorted(
        p.stem for p in CREATURES_DIR.glob("*.json")
    )
    for species_id in species_ids:
        frame = extract_idle_frame(species_id)
        frame.save(PORTRAITS_DIR / f"{species_id}.png")
        make_silhouette(frame).save(SILHOUETTES_DIR / f"{species_id}.png")
        print(f"{species_id}: portrait + silhouette ({frame.size[0]}x{frame.size[1]})")


if __name__ == "__main__":
    main()
