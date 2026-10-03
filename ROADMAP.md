# Critter Haven: Homie's Journey — Roadmap

Registro de fases do desenvolvimento. Complementa o GDD (seção 8) —
aqui fica o status real, incluindo fases que surgiram durante o
desenvolvimento e não estavam no plano original.

## Concluídas

- **Fase 0** — Auditoria e pré-produção
- **Fase 1** — Fundação técnica (janela, loop principal, always-on-top)
- **Fase 2** — Habitat e spawn
- **Fase 3** — Economia e produção
- **Fase 4** — Upgrades e progressão (upgrades, nave, planetas)
- **Fase 5** — Álbum e narrativa
- **Fase 6** — Persistência e progresso offline
- **Fase 7** — Interface desktop e integração (parte funcional: 3 estados de
  janela, always-on-top, adaptação de layout — feita antes de existir arte
  real pra aplicar visualmente; o polimento visual ficou pra Fase 8.6)
- **Fase 8** — Balanceamento e testes (simulação headless, mecânica de
  sacrificar duplicata, ajuste de curva de custo)
- **Fase 8.5** — Design e assets: sprites reais das 5 criaturas de Elyndor
  (Mossnib, Pebblit, Lumibloom, Breezel, Solarva — geradas no PixelLab,
  estilo side-scroller), habitat em camadas com profundidade real (mapa
  montado no Tiled Map Editor, `pytmx`), zonas de circulação por espécie
- **Fase 8.6** — Polimento visual de UI e menus, tudo em pixel art desenhado
  no Aseprite (via MCP): ícones da barra (Baú/Upgrades/Nave/Fusão/Álbum/
  Vender Tudo), barra de energia com líquido animado e brilho, selos de
  ouro/criaturas/itens na HUD. As 6 janelas de menu (antes ttk genérico)
  viraram painéis Canvas sem moldura do Windows, arrastáveis e sempre por
  cima: Baú (baú aberto, itens separados por criatura com seletor de
  quantidade), Upgrades (pergaminho), Nave (console estelar), Álbum (livro
  com retrato real ou silhueta por criatura descoberta/não-descoberta),
  Fusão (altar com 2 slots + lista rolável) e Configurações (painel
  metálico com switch). Mecânica de fusão substituiu o sacrifício por
  duplicata (Fase 8): funde 2 criaturas quaisquer, raridade enviesada pela
  combinação usada. Itens de cada criatura ganhando sprite próprio aos
  poucos (Mossnib/Pebblit/Lumibloom/Breezel/Solarva já têm).

## Em aberto

- **Fase 9** — Preparação para expansão: ARCHITECTURE.md, limpeza de
  config/dados e rebalanceamento do ritmo (Álbum ~1h, upgrades ~3-6h) já
  feitos; áudio (música + 12 SFX + volumes) e menu inicial feitos.
  Restam novos planetas (mais a fundo) e planejamento Steam.
- **Fase 10** — Mini tutorial inicial: Novo Jogo já dá a primeira criatura
  (Mossnib) e dicas em balões, uma por vez, avançando conforme o jogador
  age (clicar, vender no Baú, comprar upgrade, barra de energia). Salvo no
  save, pulável.
- **Fase 11** — Tower Defense + rogue-lite (libera o próximo planeta ao
  vencer waves e o chefe, no lugar do item de viagem). Decisões: criaturas
  lutam sozinhas onde estão; derrota reinicia a defesa sem perder
  criaturas (só as cartas da tentativa); batalha iniciada por um ícone
  novo na barra; produção de ouro/itens pausa durante a batalha.
  Estado: 11.1 a 11.6 implementadas (motor, papéis, waves de Elyndor, modo
  de batalha com placeholders, 13 cartas, planeta libera ao vencer a defesa);
  faltam 11.7 arte, 11.8 áudio e 11.9 balanceamento final + tutorial de combate.
  Sub-fases: 11.0 fechar design; 11.1 motor de combate em Python puro +
  simulador headless; 11.2 papéis/habilidades por espécie em dados;
  11.3 waves/inimigos/chefe de Elyndor; 11.4 modo de batalha no pygame
  (nave na cena, HUD, janela expandida); 11.5 cartas (3 por wave);
  11.6 integração com progressão/save/janela da Nave; 11.7 arte;
  11.8 áudio; 11.9 balanceamento + tutorial de combate.
- **Fase 12** — Conteúdo de defesa dos demais planetas (monstros, chefe,
  cartas de Calyra/Aerthos/Glacivar); o motor não muda, só dados.

## Pendências conhecidas (não inventar, decidir quando chegar a hora)

- Itens de viagem para Aerthos e Glacivar (GDD marca como indefinido)
- Criaturas, arte e trilha sonora de Calyra, Aerthos, Glacivar (pós-demo)
- Áudio do jogo (trilha e SFX) — ainda não iniciado
