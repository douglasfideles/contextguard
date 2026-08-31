"""ContextGuard: a defesa com estado.

Pipeline de um turno, do texto ao veredito:

    texto -> features.extract -> ConversationState.update
          -> cada Detector avalia cada alvo ativo
          -> policy.score_target (soma ponderada, desconto de mitigação)
          -> policy.decide (limiares + regra dura)  -> Verdict

Nenhuma etapa olha o futuro nem o objetivo. O que separa esta defesa do
baseline é uma coisa só: a linha `ConversationState.update`.

O modo `memoryless` existe para provar exatamente isso. Ele zera o estado antes
de cada turno, o que transforma o ContextGuard num filtro por turno — e o
resultado passa a ser igual ao do baseline. É a Reivindicação #1 do README.
"""

from __future__ import annotations

from ..detectors import build_detectors
from ..features import extract
from ..model import Turn, Verdict
from ..policy import assess, decide
from ..state import DEFAULT_HALF_LIFE, ConversationState


class ContextGuardDefense:
    """Filtro conversacional com acumulador de capacidade por alvo."""

    def __init__(
        self,
        disabled_detectors: set[str] | None = None,
        half_life: float = DEFAULT_HALF_LIFE,
        memoryless: bool = False,
        name: str | None = None,
    ) -> None:
        self.disabled_detectors = disabled_detectors or set()
        self.half_life = half_life
        self.memoryless = memoryless
        self.detectors = build_detectors(self.disabled_detectors)
        self.name = name or ("contextguard-sem-memoria" if memoryless else "contextguard")
        self.state = ConversationState(half_life=half_life)

    def reset(self) -> None:
        self.state = ConversationState(half_life=self.half_life)

    def evaluate(self, turn: Turn) -> Verdict:
        if self.memoryless:
            # Sem memória: cada turno é uma conversa nova de um turno só.
            self.state = ConversationState(half_life=self.half_life)

        features = extract(turn.index, turn.text)
        self.state.update(features)

        evidences = []
        for detector in self.detectors:
            evidence = detector.analyze(self.state, features)
            if evidence is not None:
                evidences.append((detector.weight, evidence))

        return decide(turn.index, assess(evidences, self.state))
