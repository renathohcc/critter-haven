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

import time
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
    # batalha (Fase 11.8)
    "hit_enemy": 0.35,
    "hit_ally": 0.35,
    "enemy_death": 0.5,
    "heal": 0.35,
    "wave_start": 0.7,
    "boss_appear": 0.8,
    "ship_hit": 0.5,
    "defeat": 0.8,
}

# na batalha dezenas de acertos acontecem por segundo: sem esse intervalo
# minimo o mesmo som dispararia em rajada e viraria ruido
SFX_MIN_INTERVAL = {
    "hit_enemy": 0.12,
    "hit_ally": 0.12,
    "ship_hit": 0.25,
    "enemy_death": 0.1,
    "heal": 0.3,
}
_last_played: dict[str, float] = {}

DEFAULT_USER_VOLUME = 0.5
_music_volume = DEFAULT_USER_VOLUME
_sfx_volume = DEFAULT_USER_VOLUME

_sfx_cache: dict[str, pygame.mixer.Sound | None] = {}


def play_sfx(name: str) -> None:
    min_interval = SFX_MIN_INTERVAL.get(name)
    if min_interval:
        now = time.monotonic()
        if now - _last_played.get(name, 0.0) < min_interval:
            return
        _last_played[name] = now
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
        pygame.mixer.music.set_volume(_music_level(_current_music))
    except pygame.error:
        pass


def set_sfx_volume(volume: float) -> None:
    global _sfx_volume
    _sfx_volume = max(0.0, min(1.0, volume))


def get_volumes() -> tuple[float, float]:
    return _music_volume, _sfx_volume


MUSIC_FILES = {
    "habitat": "habitat_loop.mp3",
    "battle_1": "battle_1.ogg",
    "battle_2": "battle_2.ogg",
    "final_battle": "final_battle.ogg",
}
_current_music: str | None = None

# ganho extra por faixa: as trilhas de batalha (xDeviruchi) vem masterizadas
# bem mais altas que a do habitat e devem ficar so como fundo
MUSIC_GAIN = {"habitat": 1.0, "battle_1": 0.22, "battle_2": 0.22, "final_battle": 0.22}


def _music_level(name: str | None) -> float:
    return _music_volume * HABITAT_MUSIC_VOLUME * 2 * MUSIC_GAIN.get(name or "habitat", 1.0)

# a trilha de batalha (xDeviruchi) tem intro e volta pro ponto de loop pelas
# tags LOOPSTART/LOOPLENGTH do proprio .ogg, que o SDL_mixer le sozinho


def play_music(name: str) -> None:
    """Toca a trilha `name` em loop; nao reinicia se ja for a atual."""
    global _current_music
    if name == _current_music:
        return
    music_path = AUDIO_DIR / "music" / MUSIC_FILES[name]
    if not music_path.exists():
        return
    try:
        pygame.mixer.music.load(str(music_path))
        pygame.mixer.music.set_volume(_music_level(name))
        pygame.mixer.music.play(loops=-1)
        _current_music = name
    except pygame.error:
        pass


def start_habitat_music() -> None:
    play_music("habitat")


def play_battle_music(wave_index: int, total_waves: int) -> None:
    """Primeiras waves: Battle 1; intermediarias: Battle 2; ultima: Final Battle."""
    if wave_index >= total_waves - 1:
        play_music("final_battle")
    elif wave_index < 3:
        play_music("battle_1")
    else:
        play_music("battle_2")
