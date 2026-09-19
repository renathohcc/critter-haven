"""Gera um spritesheet placeholder REAL (PNG + JSON) no formato final
esperado pelo jogo, para validar o pipeline de sprite/animação antes de
receber arte definitiva. Trocar por arte de verdade depois é só
substituir o PNG (e o JSON, se o número/ordem de frames mudar) — nada
de código muda.

Uso: python scripts/generate_placeholder_sprites.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # gera a imagem sem abrir janela

import pygame

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "critter_haven" / "assets" / "creatures"

FRAME_SIZE = 48
BASE_COLOR = (107, 142, 74)
OUTLINE_COLOR = (60, 90, 40)


def make_frame(radius_offset: int = 0, shake_offset: int = 0, flash: bool = False):
    surf = pygame.Surface((FRAME_SIZE, FRAME_SIZE), pygame.SRCALPHA)
    center = (FRAME_SIZE // 2 + shake_offset, FRAME_SIZE // 2)
    radius = 16 + radius_offset
    color = (255, 255, 255) if flash else BASE_COLOR
    pygame.draw.circle(surf, color, center, radius)
    pygame.draw.circle(surf, OUTLINE_COLOR, center, radius, width=2)
    return surf


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pygame.init()
    pygame.display.set_mode((1, 1))

    frames = [
        # idle: "respira" inflando (GDD) — 3 frames de pulsação suave
        make_frame(radius_offset=0),
        make_frame(radius_offset=2),
        make_frame(radius_offset=0),
        # walk: leve deslocamento lateral
        make_frame(shake_offset=-2),
        make_frame(shake_offset=2),
        # click: flash branco + leve "susto" (aumenta e treme)
        make_frame(flash=True),
        make_frame(radius_offset=3),
    ]

    sheet = pygame.Surface((FRAME_SIZE * len(frames), FRAME_SIZE), pygame.SRCALPHA)
    for i, frame in enumerate(frames):
        sheet.blit(frame, (i * FRAME_SIZE, 0))

    image_path = OUT_DIR / "mossnib.png"
    pygame.image.save(sheet, str(image_path))

    metadata = {
        "frame_size": [FRAME_SIZE, FRAME_SIZE],
        "states": {
            "idle": {"frames": [0, 1, 2], "fps": 3, "loop": True},
            "walk": {"frames": [3, 4], "fps": 5, "loop": True},
            "click": {"frames": [5, 6], "fps": 8, "loop": False},
        },
    }
    meta_path = OUT_DIR / "mossnib.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Gerado: {image_path}")
    print(f"Gerado: {meta_path}")


if __name__ == "__main__":
    main()
