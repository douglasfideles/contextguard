"""Detector de encadeamento anafórico.

Pergunta: *este turno só faz sentido por causa dos anteriores?*

"Junte os dois e me dê a versão final" não contém alvo, verbo perigoso nem
palavra de bloqueio. Para um filtro por turno é uma frase vazia — e é
literalmente onde o ataque colhe o resultado. O sinal só existe com memória:
é a demonstração mais direta da tese do artefato.
"""

from __future__ import annotations

from ..features import TurnFeatures
from ..model import Evidence
from ..state import ConversationState

MIN_PRIOR_TURNS = 2


class ChainingDetector:
    """Referência explícita a conteúdo sensível já acumulado."""

    name = "chaining"
    weight = 0.10

    def analyze(self, state: ConversationState, features: TurnFeatures) -> Evidence | None:
        if not features.anaphora:
            return None

        prior = [t for t in state.sensitive_turns() if t < features.index]
        if len(prior) < MIN_PRIOR_TURNS:
            return None

        strength = 0.9 if features.is_operational else 0.6
        extra = " pedindo o resultado pronto" if features.is_operational else ""
        return Evidence(
            detector=self.name,
            weight=strength,
            why=(
                f"o turno {features.index} referencia turnos sensíveis anteriores{extra}; "
                "isolado, não diz nada"
            ),
            turns=tuple(prior[-MIN_PRIOR_TURNS:] + [features.index]),
        )
