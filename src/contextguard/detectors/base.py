"""Interface comum dos detectores (padrão Strategy).

Um detector olha o estado acumulado da conversa e responde uma pergunta só.
Devolve `Evidence` quando enxerga o seu sinal, ou `None`. Nenhum detector
decide bloqueio: quem soma e decide é `policy.py`.

Acrescentar um detector novo é escrever uma classe com `name`, `weight` e
`analyze`, e registrá-la em `detectors/__init__.py`. Nada mais muda.
"""

from __future__ import annotations

from typing import Protocol

from ..features import TurnFeatures
from ..model import Evidence
from ..state import ConversationState


class Detector(Protocol):
    """Um sinal nomeado, com peso fixo na soma final."""

    name: str
    weight: float

    def analyze(self, state: ConversationState, features: TurnFeatures) -> Evidence | None:
        """Avalia o estado no turno corrente. `None` = sinal ausente."""
        ...
