"""Carrega e desenha mapas montados no Tiled (mapeditor.org, gratuito)
via pytmx. Substitui a composição de camadas feita à mão em código
(background.py) por cenários montados visualmente — o dev desenha a
posição de cada pedra/arbusto/faixa de grama no editor, em vez de mim
adivinhar coordenadas em Python.

Fluxo de trabalho:
1. Baixe o Tiled: https://www.mapeditor.org/ (gratuito, todas plataformas)
2. Crie um novo mapa (orientação ortogonal, tile size compatível com os
   tilesets em assets/tilesets/elyndor/ — a maioria usa 32x32).
3. Importe os tilesets (Tile > New Tileset > escolha o .png).
4. Monte camadas (ex: "sky", "trees_far", "ground", "decor_front") —
   nomeie livremente, o jogo desenha todas as camadas de tile na ordem
   em que aparecem no mapa.
5. Para água/tochas animadas: no editor de tileset, clique com o botão
   direito no tile > "Tile Animation Editor", monte a sequência de
   frames. O pytmx já entende isso automaticamente.
6. Salve como .tmx dentro de critter_haven/assets/tilesets/elyndor/
   (ex: elyndor.tmx) — os caminhos dos tilesets ficam relativos ao
   arquivo, então salve tudo na mesma pasta.
7. Me avise o nome do arquivo pra eu conectar no jogo.

Objetos soltos (não-grade) que você posicionar como "Object Layer" no
Tiled também são lidos por `object_positions()`, úteis pra marcar onde
o habitat deve nascer criaturas, por exemplo.
"""

from __future__ import annotations

from pathlib import Path

import pygame
import pytmx

TILESETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "tilesets"


class TileMap:
    def __init__(self, tmx_path: Path) -> None:
        self.tmx_data = pytmx.load_pygame(str(tmx_path), pixelalpha=True)
        self.pixel_width = self.tmx_data.width * self.tmx_data.tilewidth
        self.pixel_height = self.tmx_data.height * self.tmx_data.tileheight

        # tiles animados: (layer, x, y, gid) -> lista de frames pytmx já
        # resolvida, pra sobrepor a cada update() sem redesenhar o mapa
        # inteiro a cada frame.
        self._animated_tiles: list[tuple[int, int, int, list]] = []
        for layer_index, layer in enumerate(self.tmx_data.visible_layers):
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            for x, y, gid in layer.iter_data():
                if gid == 0:
                    continue
                props = self.tmx_data.tile_properties.get(gid)
                if props and props.get("frames"):
                    self._animated_tiles.append((layer_index, x, y, props["frames"]))

        self._anim_timers: dict[int, float] = {}
        self._anim_frame_index: dict[int, int] = {}

        self._base_surface = self._render_full_map()

    def _render_full_map(self) -> pygame.Surface:
        surface = pygame.Surface((self.pixel_width, self.pixel_height), pygame.SRCALPHA)
        tw, th = self.tmx_data.tilewidth, self.tmx_data.tileheight
        for layer in self.tmx_data.visible_layers:
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            for x, y, image in layer.tiles():
                if image is not None:
                    surface.blit(image, (x * tw, y * th))
        return surface

    def update(self, dt: float) -> None:
        for i, (_layer_index, _x, _y, frames) in enumerate(self._animated_tiles):
            self._anim_timers[i] = self._anim_timers.get(i, 0.0) + dt
            frame_index = self._anim_frame_index.get(i, 0)
            frame_duration = frames[frame_index].duration / 1000.0
            while self._anim_timers[i] >= frame_duration > 0:
                self._anim_timers[i] -= frame_duration
                frame_index = (frame_index + 1) % len(frames)
                frame_duration = frames[frame_index].duration / 1000.0
            self._anim_frame_index[i] = frame_index

    def render(self, target: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        """Desenha o mapa (base + frame atual dos tiles animados) na
        surface de destino, deslocado por `offset` (ex: crop de câmera)."""
        target.blit(self._base_surface, offset)
        tw, th = self.tmx_data.tilewidth, self.tmx_data.tileheight
        for i, (_layer_index, x, y, frames) in enumerate(self._animated_tiles):
            frame_index = self._anim_frame_index.get(i, 0)
            gid = frames[frame_index].gid
            image = self.tmx_data.get_tile_image_by_gid(gid)
            if image is not None:
                target.blit(image, (offset[0] + x * tw, offset[1] + y * th))

    def ground_line_y(self, layer_name: str = "Floor") -> int:
        """Y (em pixels do mapa) da linha mais alta com tile na camada de
        chão — é onde os pés das criaturas devem encostar. Cai pro fundo
        do mapa se a camada não existir ou estiver vazia."""
        try:
            layer = self.tmx_data.get_layer_by_name(layer_name)
        except ValueError:
            return self.pixel_height
        rows_with_tiles = [y for _x, y, gid in layer.iter_data() if gid != 0]
        if not rows_with_tiles:
            return self.pixel_height
        return min(rows_with_tiles) * self.tmx_data.tileheight

    def compose_for_window(
        self,
        width: int,
        height: int,
        ground_layer: str = "Floor",
        ground_margin: int = 24,
    ) -> tuple[pygame.Surface, int]:
        """Recorte ancorado na LINHA DO CHÃO (não no fundo do mapa — o mapa
        tem terra/subsolo desenhado abaixo da grama, então ancorar no fundo
        do mapa mostraria um corte subterrâneo nos estados mais baixos).
        `ground_margin` é quanto de terra sobra visível abaixo da grama.
        Corta o céu primeiro conforme a janela fica mais baixa. Retorna a
        imagem recortada e a posição em Y (na janela) onde os pés das
        criaturas devem ficar."""
        map_w, map_h = self.pixel_width, self.pixel_height
        scale = width / map_w
        new_w, new_h = width, max(1, round(map_h * scale))
        scaled = pygame.transform.smoothscale(self._base_surface, (new_w, new_h))

        scaled_ground_y = round(self.ground_line_y(ground_layer) * scale)
        crop_top = scaled_ground_y - (height - ground_margin)
        crop_top = max(0, min(crop_top, max(0, new_h - height)))

        cropped = pygame.Surface((width, height), pygame.SRCALPHA)
        cropped.blit(scaled, (0, -crop_top))

        window_ground_y = scaled_ground_y - crop_top
        return cropped, window_ground_y

    def object_positions(self, layer_name: str) -> list[dict]:
        """Objetos soltos de uma Object Layer do Tiled (nome, x, y, etc)."""
        try:
            layer = self.tmx_data.get_layer_by_name(layer_name)
        except ValueError:
            return []
        return [
            {"name": obj.name, "x": obj.x, "y": obj.y, "width": obj.width, "height": obj.height}
            for obj in layer
        ]


_map_cache: dict[str, TileMap | None] = {}


def load_map(planet_id: str, filename: str | None = None) -> TileMap | None:
    """Retorna None se o planeta ainda não tem um .tmx montado — o
    chamador cai pro background.py atual (composição em código)."""
    cache_key = f"{planet_id}/{filename}"
    if cache_key not in _map_cache:
        candidate = filename or f"{planet_id}.tmx"
        path = TILESETS_DIR / planet_id / candidate
        _map_cache[cache_key] = TileMap(path) if path.exists() else None
    return _map_cache[cache_key]
