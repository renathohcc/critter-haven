"""Música e efeitos sonoros (pygame.mixer): trilha ambiente do habitat
+ os SFX principais (clique em criatura, spawn, item, venda, compra,
fusão, viagem, clique de UI). Efeitos "bônus" (energia cheia, álbum
completo, boas-vindas, ação negada) também já existem.

Volume: música e efeitos têm cada um seu controle (0-1, ajustado na
janela de Configurações). 0.5 é o padrão e equivale à mixagem base
abaixo; 1.0 dobra (limitado a 1.0 pelo mixer).

Áudio é tratado como opcional: se o arquivo não existir ainda, ou não
houver dispositivo de som disponível, o jogo continua rodando
normalmente sem música — nunca trava a inicialização por causa disso.
"""

from __future__ import annotations

from pathlib import Path

import pygame

AUDIO_DIR = Path(__file__).resolve().parent.parent / "assets" / "audio"
HABITAT_MUSIC_VOLUME = 0.4

# volume relativo de cada efeito (0-1) -- item_drop toca com frequência,
# então fica bem mais baixo que os demais pra não cansar
SFX_VOLUMES = {
    "click_creature": 0.7,
    "spawn": 0.6,
    "item_drop": 0.25,
    "sell": 0.7,
    "buy_upgrade": 0.7,
    "fuse": 0.7,
    "travel": 0.7,
    "ui_click": 0.5,
    "denied": 0.5,
    "welcome_back": 0.7,
    "album_complete": 0.8,
    "energy_full": 0.5,
}

DEFAULT_USER_VOLUME = 0.5
_music_volume = DEFAULT_USER_VOLUME
_sfx_volume = DEFAULT_USER_VOLUME

_sfx_cache: dict[str, pygame.mixer.Sound | None] = {}


def play_sfx(name: str) -> None:
    if name not in _sfx_cache:
        path = AUDIO_DIR / "sfx" / f"{name}.mp3"
        try:
            sound = pygame.mixer.Sound(str(path)) if path.exists() else None
        except pygame.error:
            sound = None
        _sfx_cache[name] = sound
    sound = _sfx_cache[name]
    if sound is not None:
        sound.set_volume(min(1.0, SFX_VOLUMES.get(name, 0.7) * _sfx_volume * 2))
        sound.play()


def set_music_volume(volume: float) -> None:
    global _music_volume
    _music_volume = max(0.0, min(1.0, volume))
    try:
        pygame.mixer.music.set_volume(_music_volume * HABITAT_MUSIC_VOLUME * 2)
    except pygame.error:
        pass


def set_sfx_volume(volume: float) -> None:
    global _sfx_volume
    _sfx_volume = max(0.0, min(1.0, volume))


def get_volumes() -> tuple[float, float]:
    return _music_volume, _sfx_volume


def start_habitat_music() -> None:
    music_path = AUDIO_DIR / "music" / "habitat_loop.mp3"
    if not music_path.exists():
        return
    try:
        pygame.mixer.music.load(str(music_path))
        pygame.mixer.music.set_volume(_music_volume * HABITAT_MUSIC_VOLUME * 2)
        pygame.mixer.music.play(loops=-1)
    except pygame.error:
        pass
