"""Mini tutorial inicial (Fase 10): uma dica por vez, que só avança
quando o jogador faz a ação ensinada. Python puro -- o desenho do balão e
do destaque fica em render/tutorial_hint.py."""

from __future__ import annotations

from dataclasses import dataclass

# (passo, evento que o conclui, texto da dica, o que destacar na tela)
# "creature" = a criatura; "bar" = barra de energia; "btn_*" = ícone da HUD
STEPS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("click_creature", "creature_clicked",
     "Bem-vindo! Esta é a sua primeira criatura. Clique nela para fazer carinho.",
     ("creature",)),
    ("wait_item", "item_dropped",
     "Boa! Criaturas soltam itens de tempos em tempos, e eles vão pro Baú. Aguarde o primeiro.",
     ("creature",)),
    ("open_chest", "chest_opened",
     "Um item caiu! Abra o Baú para ver o que você tem.",
     ("btn_bau",)),
    ("sell", "sold",
     "Itens valem ouro. Venda pelo Baú (item a item) ou use o botão Vender Tudo.",
     ("btn_bau", "btn_vender_tudo")),
    ("buy_upgrade", "upgrade_bought",
     "Com ouro você compra upgrades. Abra Upgrades e compre o primeiro.",
     ("btn_upgrades",)),
    ("energy_info", "spawned",
     "Quando a barra de energia enche, nasce uma nova criatura. Descubra todas!",
     ("bar",)),
)

DONE = "done"
ENERGY_INFO_MAX_SECONDS = 14.0
_STEP_NAMES = tuple(s[0] for s in STEPS)


@dataclass
class Tutorial:
    step: str = DONE
    _info_timer: float = 0.0

    @classmethod
    def new_game(cls) -> "Tutorial":
        return cls(step=STEPS[0][0])

    @classmethod
    def from_saved(cls, step: str | None) -> "Tutorial":
        # save antigo (sem a chave) ou nome desconhecido: nao mostra nada
        return cls(step=step if step in _STEP_NAMES else DONE)

    @property
    def active(self) -> bool:
        return self.step != DONE

    def _current(self) -> tuple[str, str, str, tuple[str, ...]] | None:
        for entry in STEPS:
            if entry[0] == self.step:
                return entry
        return None

    @property
    def text(self) -> str:
        entry = self._current()
        return entry[2] if entry else ""

    @property
    def highlights(self) -> tuple[str, ...]:
        entry = self._current()
        return entry[3] if entry else ()

    def on_event(self, event: str) -> None:
        entry = self._current()
        if entry is None or entry[1] != event:
            return
        index = _STEP_NAMES.index(self.step)
        self.step = _STEP_NAMES[index + 1] if index + 1 < len(_STEP_NAMES) else DONE
        self._info_timer = 0.0

    def tick(self, dt: float) -> None:
        # o ultimo passo e so informativo: some sozinho depois de um tempo
        if self.step == "energy_info":
            self._info_timer += dt
            if self._info_timer >= ENERGY_INFO_MAX_SECONDS:
                self.step = DONE

    def skip(self) -> None:
        self.step = DONE
