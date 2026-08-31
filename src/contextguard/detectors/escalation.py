"""Detector de escalada de especificidade.

Pergunta: *o pedido saiu do conceitual e chegou ao operacional?*

A decomposição multi-turno tem uma assinatura estável: começa perguntando como
uma coisa funciona e termina pedindo o comando pronto. Cada ponta é banal; o
percurso é que informa. Só o nível operacional isolado não basta — muita gente
legítima pede comando pronto —, por isso o detector exige a **subida**: um turno
sensível anterior menos específico.
"""

from __future__ import annotations

from ..features import TurnFeatures
from ..model import Evidence
from ..state import ConversationState

LEVEL_NAMES = {0: "conceitual", 1: "específico", 2: "operacional"}


class EscalationDetector:
    """Trajetória conceitual → específico → operacional na conversa."""

    name = "escalation"
    weight = 0.20

    def analyze(self, state: ConversationState, features: TurnFeatures) -> Evidence | None:
        operational_turn = state.level_turn(2)
        if operational_turn is None:
            return None  # ainda não chegou ao operacional: não há escalada

        earlier = {
            lvl: state.level_turns[lvl]
            for lvl in (0, 1)
            if state.level_turns.get(lvl) is not None
            and state.level_turns[lvl] < operational_turn
        }
        if not earlier:
            return None  # pediu operacional de saída: é outro sinal, não escalada

        strength = min(1.0, 0.6 + 0.2 * len(earlier))  # 2 níveis -> 0.8 ; 3 -> 1.0
        path = " → ".join(LEVEL_NAMES[lvl] for lvl in sorted(set(earlier) | {2}))
        return Evidence(
            detector=self.name,
            weight=strength,
            why=f"os pedidos escalaram {path}",
            turns=tuple(sorted(set(earlier.values()) | {operational_turn})),
        )
