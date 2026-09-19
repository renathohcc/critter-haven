"""Monta spritesheet+JSON a partir de GIFs de animação exportados pelo
PixelLab (um GIF por estado/direção, já com transparência).

Uso: edite o dicionário ANIMATIONS abaixo apontando pros GIFs certos e
rode. Cada entrada vira um "estado" no JSON (idle, walk_left, ...).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "critter_haven" / "assets" / "creatures"


def gif_frames(path: Path) -> list[Image.Image]:
    img = Image.open(path)
    return [frame.convert("RGBA").copy() for frame in ImageSequence.Iterator(img)]


def assemble(species_id: str, animations: dict[str, tuple[Path, bool]]) -> None:
    all_frames: list[Image.Image] = []
    states: dict[str, dict] = {}
    frame_w = frame_h = None

    for state_name, (gif_path, loop) in animations.items():
        frames = gif_frames(gif_path)
        if frame_w is None:
            frame_w, frame_h = frames[0].size
        elif frames[0].size != (frame_w, frame_h):
            raise ValueError(f"{gif_path} tem tamanho diferente dos demais")

        start = len(all_frames)
        all_frames.extend(frames)
        states[state_name] = {
            "frames": list(range(start, start + len(frames))),
            "fps": 8,
            "loop": loop,
        }

    sheet = Image.new("RGBA", (frame_w * len(all_frames), frame_h), (0, 0, 0, 0))
    for i, frame in enumerate(all_frames):
        sheet.paste(frame, (i * frame_w, 0))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT_DIR / f"{species_id}.png")
    (OUT_DIR / f"{species_id}.json").write_text(
        json.dumps({"frame_size": [frame_w, frame_h], "states": states}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"{species_id}: {len(all_frames)} frames, estados={list(states.keys())}")


if __name__ == "__main__":
    IMAGES_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    assemble(
        "mossnib",
        {
            "idle": (IMAGES_DIR / "22.gif", True),         # grupo2, frente
            "walk_left": (IMAGES_DIR / "23.gif", True),    # grupo3, esquerda
            "walk_right": (IMAGES_DIR / "25.gif", True),   # grupo3, direita
            "click": (IMAGES_DIR / "18.gif", False),       # grupo1, frente
        },
    )
