"""Monta spritesheet+JSON a partir de GIFs de animação exportados pelo
PixelLab (um GIF por estado/direção, já com transparência).

Animações diferentes às vezes vêm em canvas de tamanho ligeiramente
diferente (ex: idle 64x64, walk 60x60) — em vez de re-escalar (o que
borra pixel art), completamos com transparência até o maior tamanho,
centralizado, preservando os pixels originais intactos.

Uso: chame assemble() com o dicionário de animações, ou edite o bloco
no fim do arquivo e rode `python scripts/assemble_pixellab_animations.py <pasta>`.
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


def _pad_to(frame: Image.Image, target_w: int, target_h: int) -> Image.Image:
    if frame.size == (target_w, target_h):
        return frame
    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    x = (target_w - frame.width) // 2
    y = (target_h - frame.height) // 2
    canvas.paste(frame, (x, y), frame)
    return canvas


def assemble(species_id: str, animations: dict[str, tuple[Path, bool]]) -> None:
    raw: dict[str, list[Image.Image]] = {
        state: gif_frames(gif_path) for state, (gif_path, _loop) in animations.items()
    }

    frame_w = max(f.width for frames in raw.values() for f in frames)
    frame_h = max(f.height for frames in raw.values() for f in frames)

    all_frames: list[Image.Image] = []
    states: dict[str, dict] = {}
    for state_name, (_gif_path, loop) in animations.items():
        frames = [_pad_to(f, frame_w, frame_h) for f in raw[state_name]]
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
    print(f"{species_id}: {len(all_frames)} frames ({frame_w}x{frame_h}), estados={list(states.keys())}")


if __name__ == "__main__":
    IMAGES_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    assemble(
        "pebblit",
        {
            "idle": (IMAGES_DIR / "55.gif", True),
            "walk_left": (IMAGES_DIR / "53.gif", True),
            "walk_right": (IMAGES_DIR / "54.gif", True),
            "click": (IMAGES_DIR / "52.gif", False),
        },
    )
