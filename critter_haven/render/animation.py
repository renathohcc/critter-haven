"""State machine de animação por criatura: qual frame mostrar agora,
dado o tempo passado e o estado desejado (idle/walk/click).

O estado de animação vive aqui (camada de render), não na entidade —
`Creature` não sabe nada sobre frames ou fps. Usamos um
WeakKeyDictionary para que o estado suma sozinho quando a criatura é
removida do habitat (ex: sacrificada como duplicata), sem precisar de
limpeza manual.
"""

from __future__ import annotations

import weakref
from dataclasses import dataclass

import pygame

from critter_haven.render.spritesheet import SpriteSheet


@dataclass
class _AnimationState:
    state: str = "idle"
    frame_index: int = 0
    timer: float = 0.0


_states: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def current_frame(
    creature: object, sheet: SpriteSheet, desired_state: str, dt: float
) -> pygame.Surface:
    if not sheet.has_state(desired_state):
        desired_state = "idle"

    anim = _states.get(creature)
    if anim is None:
        anim = _AnimationState(state=desired_state)
        _states[creature] = anim
    elif anim.state != desired_state:
        anim.state = desired_state
        anim.frame_index = 0
        anim.timer = 0.0

    frames = sheet.state_frames(anim.state)
    fps = sheet.state_fps(anim.state)
    loop = sheet.state_loops(anim.state)
    frame_duration = 1.0 / fps if fps > 0 else 1.0

    anim.timer += dt
    while anim.timer >= frame_duration:
        anim.timer -= frame_duration
        anim.frame_index += 1
        if anim.frame_index >= len(frames):
            anim.frame_index = 0 if loop else len(frames) - 1

    return frames[anim.frame_index]
