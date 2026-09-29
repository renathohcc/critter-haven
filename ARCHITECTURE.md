# Arquitetura — Critter Haven: Homie's Journey

Este documento existe pra quem (humano ou IA) precisar retomar o projeto
depois de um tempo e não lembrar como as peças se encaixam. Complementa o
GDD (que define *o quê* o jogo faz) e o `ROADMAP.md` (que registra *quando*
cada parte foi feita) — aqui é *como* o código está organizado e *por quê*
algumas decisões não óbvias foram tomadas.

## Visão geral

Jogo idle/incremental cozy em Python + `pygame-ce`, pensado pra rodar como
uma janela pequena e "sempre no topo" no desktop (Windows), com menus
auxiliares abertos em janelas Tkinter separadas por cima do jogo. Não há
engine externa — é um loop de jogo Pygame de verdade, com os menus vivendo
numa thread Tkinter à parte.

```
main.py → critter_haven/core/app.py (App, o loop principal)
```

## Camadas (por que o código está dividido assim)

A regra que se manteve o projeto inteiro: **entidades, economia e sistemas
são Python puro, sem import de pygame ou tkinter.** Só as camadas `render/`
e `ui/` conhecem essas bibliotecas. Isso é o que permite os testes em
`tests/` rodarem em milissegundos sem abrir janela nenhuma (`pytest` puro,
sem mocks de GUI) e o `scripts/simulate_balance.py` simular horas de jogo
sem renderizar um único frame.

```
config/       → dataclasses "congeladas" com números de balanceamento
                (GDD + decisões tomadas em conversa, nunca inventados)
data/         → carrega critter_haven/data/creatures.json (espécies)
entities/     → Creature, Habitat, Album — estado do jogo, puro Python
economy/      → Wallet, Chest, upgrades, preços — puro Python
systems/      → funções que conectam entidades+economia (produção,
                progresso offline, viagem, sorteio de spawn/fusão)
persistence/  → serialização do save em JSON
render/       → tudo que desenha em cima de uma Surface do pygame
ui/           → as janelas de menu em Tkinter
core/         → App (o loop), MenuBridge (ponte entre as duas threads),
                window.py (always-on-top via win32)
```

Se uma dúvida futura for "isso é regra de jogo ou é desenho na tela?", a
resposta geralmente decide em qual dessas pastas a mudança entra.

## O loop principal (`core/app.py`)

`App.run()` é um loop clássico: entrada → atualiza estado → publica
snapshot pro menu → desenha. Cada frame:

1. `_handle_events` — cliques do mouse (ícones da HUD, criaturas)
2. `_process_menu_commands` — drena comandos que vieram do Tkinter
   (comprar upgrade, vender item, viajar, fundir...)
3. `_update` — avança habitat/produção/timers
4. `_publish_menu_snapshot` — serializa o estado atual num dict e manda
   pro `MenuBridge` (é isso que as janelas Tkinter leem pra se redesenhar)
5. `_render` — desenha tudo na Surface do pygame

FPS é dinâmico (`FPS_FOCUSED`/`FPS_UNFOCUSED`): cai bastante quando a janela
não está em foco, checado via win32 direto (`core/window.py`) porque os
eventos de foco do SDL ficam pouco confiáveis com a janela em modo
always-on-top.

## Janelas de menu (`ui/`) — o padrão que se repete em todas

Cada menu (Baú, Upgrades, Nave, Álbum, Fusão, Configurações) é uma classe
independente com essa mesma interface "duck-typed" (sem herança comum —
ver `ui/menu_window.py::WINDOW_CLASSES`):

```python
class AlgumWindow:
    window_name = "algum_id"          # chave usada no MenuBridge
    def __init__(self, root, bridge): ...
    def sync_visibility(self) -> None: ...   # mostra/esconde
    def refresh(self, snapshot: dict) -> None: ...  # redesenha com dados novos
```

`ui/menu_window.py::run_menu_window` roda numa **thread própria** (ver
`App.__init__`), cria um `tk.Tk()` raiz escondido e instancia todas as
janelas uma vez só. O loop de poll (a cada 200ms) chama `sync_visibility()`
e, se visível, `refresh(snapshot)` em cada uma.

### Por que cada janela é sem moldura do Windows

Todas usam a mesma receita (veja qualquer uma em `ui/*_window.py`):

```python
self.top.overrideredirect(True)                      # sem titlebar/borda
self.top.attributes("-transparentcolor", "#ff00ff")  # essa cor vira invisível
self.top.attributes("-topmost", True)                # sempre acima do jogo
```

O Canvas é pintado com essa cor-chave fora da arte (cantos arredondados,
abas que "saem" da lateral no Álbum, etc.) — o Windows trata esses pixels
como transparentes *e* clicáveis-através, então a janela parece um objeto
flutuando, não um programa. Como não existe titlebar, cada janela desenha
seu próprio botão de fechar (`close_x.png`) e implementa arrastar à mão
(bind de `<ButtonPress-1>`/`<B1-Motion>` na imagem de fundo).

### `MenuBridge` (`core/menu_bridge.py`) — a única ponte entre as threads

Nunca lemos/escrevemos o estado do jogo direto de dentro de uma janela
Tkinter (evita duas threads mexendo no mesmo objeto ao mesmo tempo). Tudo
passa por filas simples:

- `publish(snapshot)` / `read_snapshot()` — App publica um dict a cada
  frame; as janelas só leem.
- `push_command(nome, payload)` / `drain_commands()` — clique no menu vira
  um comando que o loop do `App` aplica no próximo frame
  (`_process_menu_commands`).
- `push_to_menu(nome, payload)` / `drain_to_menu_commands()` — sentido
  contrário: a HUD do pygame pede pro Tkinter fazer algo (hoje só
  `"show_window"`, quando o jogador clica um ícone).
- `show_window(nome)` / `hide_window(nome)` / `is_window_visible(nome)` —
  visibilidade por janela.

### Listas roláveis dentro de uma janela sem moldura

O menu de Fusão precisa listar um número variável de criaturas. A solução
(ver `ui/fusion_window.py::_build_list_canvas`) é colocar um **Canvas
filho** com tamanho fixo dentro do Canvas principal via
`canvas.create_window(...)`. O Tkinter recorta automaticamente qualquer
conteúdo que passe dos limites de um widget Canvas — é a única forma de
garantir que os cards nunca vazem pro fundo da janela, e ainda dá scroll de
graça (`yscrollincrement` + bind de `<MouseWheel>`).

### A cilada do texto que "sobrepõe o botão"

Aconteceu umas 3 vezes durante a Fase 8.6: um texto que cabia direitinho no
mockup (gerado com Pillow) invadia o botão ao lado *só na tela real* do
dev. Causa: a fonte do Tkinter escala com o DPI do Windows (o monitor de
teste roda a 125%), então o mesmo texto pode renderizar bem mais largo do
que os pixels da arte estática sugerem — e isso não aparece testando só
com Pillow (que não passa pelo mesmo motor de fonte). A correção definitiva
não foi "aumentar a margem" (funciona só até o próximo nome comprido), foi
medir a largura real com `tkinter.font.Font(...).measure(texto)` e encolher
o tamanho da fonte (ou truncar com "…") até caber — ver `_fit_text` em
`ui/upgrades_window.py`, `ui/nave_window.py` e `ui/settings_window.py`.
Qualquer coluna de texto nova ao lado de um botão deveria reusar esse
padrão em vez de confiar num max_width chutado.

## Pipeline de assets

Nada de arte é gerado em runtime — tudo é pré-processado uma vez e commitado
como PNG. Três origens, três fluxos:

**1. Sprites de criatura** (PixelLab, externo) — o dev gera as animações no
PixelLab, `scripts/assemble_pixellab_animations.py` junta os frames num
spritesheet único (`assets/creatures/<id>.png` + `.json` com os estados);
`scripts/generate_album_portraits.py` deriva os retratos (frame idle
ampliado) e as silhuetas (mesmo alpha, preenchido de preto) usadas no
Álbum — reaproveita a arte real, não inventa outra.

**2. Ícones/UI/molduras** (Aseprite, via MCP) — toda a HUD e os fundos das
janelas de menu foram desenhados chamando as ferramentas do Aseprite MCP
(`mcp__aseprite__*`) diretamente nesta sessão: formas simples (retângulos,
círculos, texto bitmap 3x5/5x7 próprio) compostas em Lua via
`script_execute` quando o desenho tinha muita repetição (ex: o texto
pixelado dos botões). Ver qualquer PNG em `assets/ui/` — todos seguem a
mesma paleta (`#090202` borda escura, `#3B3634`/`#603D24` madeira,
`#F4D693` dourado — e um tom de destaque por janela: violeta na Fusão,
azul-arroxeado na Nave, aço na Config). Ao pedir um ícone novo, reusar
essa paleta em vez de inventar cores novas mantém tudo com cara de
"mesmo jogo".

**3. Ícones de item** (o dev gera externamente, ex: ferramentas de IA
generativa) — chegam como PNG grande (ex: 1254×1254) com fundo já
transparente; só precisam de crop na bounding box do conteúdo +
redimensionamento (`Image.LANCZOS`) pra ~64×64 antes de salvar em
`assets/items/<species_id>.png`. `ui/chest_window.py` carrega esse arquivo
se existir, senão cai pro retrato da criatura como placeholder.

**Regra geral do projeto**: Pillow é dependência só de `scripts/` (pipeline
de asset, roda uma vez, offline). Runtime (o jogo em si) nunca importa
`PIL` — só carrega os PNGs já prontos via `pygame.image.load` ou
`tkinter.PhotoImage`.

## Escalonamento de pixel art (nearest-neighbor sempre)

Dois pontos onde isso importa:

- **pygame** (`render/ui_icons.py`, `render/stat_badge.py`, etc.): usar
  `pygame.transform.scale`, nunca `smoothscale` — o antialiasing do
  smoothscale borra contornos de pixel art ao reduzir, dando um aspecto
  "derretido". Ícones grandes são desenhados a 2x o tamanho de exibição
  final (ex: 96px de altura pra exibir a 48px) pra um downscale 2:1 exato,
  sem aliasing.
- **Tkinter** (`ui/*_window.py`): `tk.PhotoImage` não tem scale suave — só
  `.zoom(n)` (amplia por inteiro) e `.subsample(n)` (reduz por inteiro).
  Pra caber um retrato de criatura numa caixa de ícone fixa, ver o padrão
  em `ChestWindow._get_item_icon`: se menor que a caixa, `zoom`; se maior,
  `subsample(ceil(largura/caixa))`.

## Persistência e progresso offline

Save é um JSON simples (`persistence/save_file.py` + `serializer.py`).
Progresso offline (`systems/offline_progress.py`) é calculado
**analiticamente** a partir do timestamp salvo — nunca simulando o jogo
segundo a segundo — pra não travar a abertura do jogo depois de várias
horas fechado.

## Testes

`pytest` puro (sem pytest-qt nem screenshot automatizado) cobrindo
`entities/`, `economy/`, `systems/`, `persistence/`. Roda em <1s porque
nada ali importa pygame/tkinter. Antes de qualquer mudança visual (Tkinter),
a validação é: rodar o teste isolado do módulo com uma captura de tela real
(padrão usado a Fase 8.6 inteira: um script standalone em
`scratchpad/test_*_window.py` que instancia só aquela janela, publica um
snapshot fake no bridge, e usa `PIL.ImageGrab` pra tirar print antes de
mexer no jogo de verdade — pega bugs de layout sem precisar abrir o jogo
inteiro a cada iteração).

## Convenções de código

- Comentários só explicam o *porquê* não óbvio (uma decisão de design, um
  bug específico que motivou o código daquele jeito) — nunca o *o quê*
  (isso o nome da variável/função já diz).
- Sem abstração prematura: se só existem 5 espécies numa lista, não vira
  um sistema de plugins.
- Commits diretos na `main` (sem PRs/branches — fluxo de projeto solo),
  mensagem descrevendo o *porquê* da mudança, terminando com
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

## Adicionando um novo planeta (quando Calyra/Aerthos/Glacivar tiverem conteúdo)

O suporte parcial já existe — pontos que provavelmente precisam de ajuste:

1. `data/creatures.json` — adicionar a chave do planeta com a lista de
   espécies (mesmo formato de Elyndor).
2. `config/planets.py` — já tem as 4 entradas; `active`/`required_item`
   precisam ser preenchidos quando o requisito de viagem for decidido
   (hoje `requirement_pending=True` pra Aerthos/Glacivar — GDD marca como
   indefinido, não inventar).
3. `ui/album_window.py::_load_chapters` — já filtra só planetas com
   `species_pool` não vazio; o capítulo aparece sozinho assim que o JSON
   tiver espécies.
4. `ui/nave_window.py::PLANET_COLORS` — precisa de uma cor temática pro
   novo planeta (hoje só tem as 4 já cadastradas).
5. Sprites/retratos/silhuetas/itens de cada nova criatura seguem o mesmo
   pipeline da seção "Pipeline de assets" acima.
6. `config/habitat_zones.py` — se o novo planeta tiver zonas de circulação
   por espécie diferentes de "andar livre no habitat inteiro", precisa de
   entradas em `SPECIES_ROAM_FRACTIONS`/`STATIONARY_SPECIES`.

Nenhum desses pontos exige mudança estrutural — é só popular dados.
