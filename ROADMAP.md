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

- **Fase 9** — Preparação para expansão (documentar arquitetura, organizar
  dados, preparar suporte a novos planetas, próximos passos de áudio e
  distribuição Steam)

## Pendências conhecidas (não inventar, decidir quando chegar a hora)

- Itens de viagem para Aerthos e Glacivar (GDD marca como indefinido)
- Criaturas, arte e trilha sonora de Calyra, Aerthos, Glacivar (pós-demo)
- Áudio do jogo (trilha e SFX) — ainda não iniciado
