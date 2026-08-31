"""Detector de persistência de alvo.

Pergunta: *algum ativo sensível é o eixo da conversa, ou só passou por ela?*

Citar credenciais uma vez é ruído. Voltar a elas em vários turnos, com o peso
recente ainda alto, é intenção. É o sinal mais fraco dos cinco — sozinho não
chega perto de bloquear — e serve como reforço de contexto para os demais.
"""

from __future__ import annotations

from ..features import TurnFeatures
from ..model import Evidence
from ..state import ConversationState

MIN_PRESENCE = 2.0    # turnos "equivalentes", já descontado o decaimento
FULL_PRESENCE = 4.0   # a partir daqui o sinal satura


class TargetPersistenceDetector:
    """Reincidência de um mesmo ativo sensível ao longo da conversa."""

    name = "target_persistence"
    weight = 0.15

    def analyze(self, state: ConversationState, features: TurnFeatures) -> Evidence | None:
        asset, presence = state.persistent_asset()
        if asset is None or presence < MIN_PRESENCE:
            return None

        strength = min(1.0, (presence - MIN_PRESENCE) / (FULL_PRESENCE - MIN_PRESENCE))
        turns = state.assets[asset].turns
        return Evidence(
            detector=self.name,
            weight=strength,
            why=f"'{asset}' reaparece em {len(turns)} turnos (presença {presence:.1f} após decaimento)",
            turns=tuple(turns),
        )
