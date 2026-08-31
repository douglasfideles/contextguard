"""Detector de composição — o núcleo do ContextGuard.

Pergunta: *quantas etapas distintas da cadeia de ataque esta conversa já
cobriu, sobre conteúdo sensível?*

Nenhuma peça é uma arma. Perguntar como localizar funcionários é RH; perguntar
como montar um formulário é desenvolvimento web; perguntar como não cair no
filtro de spam é marketing. As três juntas, em poucos turnos e em nível
operacional, são uma operação de phishing — e é isso que um filtro por turno não
tem como ver, porque a informação não está em nenhum turno: está na *união*
deles.

O paralelo com a cadeia de ataque (reconhecimento → acesso → artefato → entrega
→ evasão → impacto) é conhecido e antigo; a contribuição aqui é aplicá-lo ao
texto de uma conversa em vez de a eventos de rede.
"""

from __future__ import annotations

from ..features import TurnFeatures
from ..model import Evidence
from ..state import ConversationState

MIN_PHASES = 2    # a partir daqui há sinal


class CompositionDetector:
    """Acúmulo de fases da cadeia de ataque ao longo da conversa."""

    name = "composition"
    weight = 0.40

    def analyze(self, state: ConversationState, features: TurnFeatures) -> Evidence | None:
        phases = state.recent_phases()
        if len(phases) < MIN_PHASES:
            return None

        operational = state.max_level == 2
        # 2 fases -> 0.5 ; 3 fases -> 1.0 ; +0.25 se já em nível operacional.
        strength = min(1.0, (len(phases) - 1) / 2 + (0.25 if operational else 0.0))

        labels = ", ".join(sorted(phases))
        detail = "em nível operacional" if operational else "ainda não operacional"
        return Evidence(
            detector=self.name,
            weight=strength,
            why=f"a conversa já cobriu {len(phases)} etapas da cadeia ({labels}), {detail}",
            turns=tuple(sorted(phases.values())),
        )
