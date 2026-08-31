"""Agregação das evidências e decisão final do turno.

Separado dos detectores de propósito: os detectores respondem "vi este sinal";
a política responde "e daí". Trocar limiares, mudar a escala ou introduzir uma
nova regra dura acontece aqui, num arquivo curto que dá para ler inteiro antes
de uma reunião.

Escala: cada detector tem peso fixo e os pesos somam 1.0, então o score bruto
vive em [0, 1] e os limiares abaixo são lidos como fração do sinal máximo.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import Decision, Evidence, Verdict
from .state import ConversationState

FLAG_THRESHOLD = 0.40
BLOCK_THRESHOLD = 0.60

# Posse/autorização/intenção defensiva declaradas descontam até 40% do score.
# Desconto, não imunidade: a afirmação é auto-declarada e portanto falsificável
# (ver o cenário evasivo `*_autoridade` e a discussão no RELATORIO.md).
MAX_MITIGATION = 0.40

# Acima desta força de mitigação, a regra dura é suspensa.
HARD_SUPPRESSION = 0.6


@dataclass(frozen=True)
class Assessment:
    """O score da conversa no turno corrente, com o que o produziu."""

    raw: float
    adjusted: float
    mitigation: float
    evidences: tuple[Evidence, ...]
    hard: bool


# Regra dura: a conversa juntou, em nível operacional e sobre conteúdo sensível,
# ou 3 etapas distintas da cadeia, ou 2 etapas depois de escalar até o
# operacional. É o momento em que peças inofensivas viram uma capacidade — a
# decisão não depende do score contínuo, que a diluição consegue rebaixar.
#
# A regra é derivada das EVIDÊNCIAS, não do estado bruto: ela só dispara se o
# detector de composição (e, no caso de 2 fases, o de escalada) tiver de fato
# apontado o sinal. Assim, desligar um desses detectores na ablação (R4)
# realmente desarma o caminho de bloqueio — um detector que dá para desligar sem
# efeito não estaria pagando o seu lugar.
HARD_PHASES = 3           # 3 fases + operacional já bastam, mesmo sem escalada explícita
HARD_PHASES_ESCALATED = 2  # 2 fases bastam se houve escalada até o operacional


def _hard_rule(evidences: list[tuple[float, Evidence]], state: ConversationState) -> bool:
    if state.max_level != 2:
        return False
    detectors = {ev.detector for _, ev in evidences}
    if "composition" not in detectors:
        return False
    n_phases = len(state.recent_phases())
    if n_phases >= HARD_PHASES:
        return True
    return n_phases >= HARD_PHASES_ESCALATED and "escalation" in detectors


def assess(
    evidences: list[tuple[float, Evidence]], state: ConversationState
) -> Assessment:
    """Soma ponderada das evidências, descontada a mitigação da conversa."""
    raw = min(1.0, sum(detector_weight * ev.weight for detector_weight, ev in evidences))
    mitigation = state.mitigation_strength()
    adjusted = raw * (1.0 - MAX_MITIGATION * mitigation)
    hard = (
        (any(ev.hard for _, ev in evidences) or _hard_rule(evidences, state))
        and mitigation < HARD_SUPPRESSION
    )
    return Assessment(
        raw=raw,
        adjusted=adjusted,
        mitigation=mitigation,
        evidences=tuple(ev for _, ev in evidences),
        hard=hard,
    )


def decide(turn_index: int, assessment: Assessment) -> Verdict:
    """Veredito do turno a partir do score agregado e da regra dura."""
    if not assessment.evidences:
        return Verdict(turn_index=turn_index, decision=Decision.ALLOW, score=0.0)

    if assessment.hard:
        decision = Decision.BLOCK
    elif assessment.adjusted >= BLOCK_THRESHOLD:
        decision = Decision.BLOCK
    elif assessment.adjusted >= FLAG_THRESHOLD:
        decision = Decision.FLAG
    else:
        decision = Decision.ALLOW

    evidences = assessment.evidences
    if assessment.hard:
        evidences = evidences + (
            Evidence(
                detector="policy",
                weight=1.0,
                why=(
                    "regra dura: a conversa juntou etapas da cadeia em nível operacional "
                    "sobre conteúdo sensível, sem autorização declarada"
                ),
                hard=True,
            ),
        )
    if assessment.mitigation > 0:
        evidences = evidences + (
            Evidence(
                detector="mitigation",
                weight=assessment.mitigation,
                why=(
                    f"posse/autorização/intenção defensiva declarada reduziu o score "
                    f"de {assessment.raw:.2f} para {assessment.adjusted:.2f}"
                ),
            ),
        )

    return Verdict(
        turn_index=turn_index,
        decision=decision,
        score=round(assessment.adjusted, 4),
        evidences=evidences,
    )
