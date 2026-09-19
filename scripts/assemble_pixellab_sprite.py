"""Monta o spritesheet de uma criatura a partir das rotações exportadas
pelo PixelLab (west/east, viradas pra esquerda/direita — é só isso que
usamos, já que as criaturas só andam no eixo horizontal no habitat).

Uso:
    python scripts/assemble_pixellab_sprite.py <species_id> <pasta_rotations>

Exemplo:
    python scripts/assemble_pixellab_sprite.py mossnib \
        "C:\\Users\\renat\\Downloads\\Pixel_art_character_spri-Idle\\Idle\\rotations"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "critter_haven" / "assets" / "creatures"


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(1)

    species_id = sys.argv[1]
    rotations_dir = Path(sys.argv[2])

    west = Image.open(rotations_dir / "west.png").convert("RGBA")
    east = Image.open(rotations_dir / "east.png").convert("RGBA")
    south = Image.open(rotations_dir / "south.png").convert("RGBA")
    if not (west.size == east.size == south.size):
        raise ValueError(
            f"rotações com tamanhos diferentes: west={west.size} east={east.size} south={south.size}"
        )

    frame_w, frame_h = west.size
    sheet = Image.new("RGBA", (frame_w * 3, frame_h), (0, 0, 0, 0))
    sheet.paste(west, (0, 0))
    sheet.paste(east, (frame_w, 0))
    sheet.paste(south, (frame_w * 2, 0))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    image_path = OUT_DIR / f"{species_id}.png"
    sheet.save(image_path)

    metadata = {
        "frame_size": [frame_w, frame_h],
        "states": {
            "walk_left": {"frames": [0], "fps": 1, "loop": True},
            "walk_right": {"frames": [1], "fps": 1, "loop": True},
            "idle": {"frames": [2], "fps": 1, "loop": True},
        },
    }
    meta_path = OUT_DIR / f"{species_id}.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    # Guarda o retrato de frente à parte — não faz parte da spritesheet de
    # gameplay, mas fica pronto pro Álbum usar como ícone no futuro.
    south_src = rotations_dir / "south.png"
    if south_src.exists():
        portrait_dir = OUT_DIR / "portraits"
        portrait_dir.mkdir(parents=True, exist_ok=True)
        Image.open(south_src).convert("RGBA").save(portrait_dir / f"{species_id}.png")
        print(f"Retrato salvo: {portrait_dir / f'{species_id}.png'}")

    print(f"Gerado: {image_path}")
    print(f"Gerado: {meta_path}")


if __name__ == "__main__":
    main()
