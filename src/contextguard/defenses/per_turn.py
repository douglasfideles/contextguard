"""Baseline: filtro sem estado, que olha uma pergunta por vez.

É o alvo da crítica do desafio — e precisa ser um adversário honesto, não um
espantalho. Por isso ele tem duas regras, e não uma:

1. **Lista de bloqueio explícita.** Frases inequívocas, do tipo que qualquer
   filtro de produção carrega.
2. **Composição dentro de um único turno.** Se *o mesmo turno* junta um ativo
   sensível, duas ou mais etapas da cadeia e um pedido operacional, bloqueia.
   É a mesma ideia do ContextGuard, com a janela reduzida a um turno.

A regra 2 é o que torna a comparação justa: o baseline não perde por ser burro,
perde por **não ter memória**. Os cenários `*_turno_unico` provam isso — são o
mesmo objetivo pedido de uma vez, e o baseline bloqueia todos.

O baseline decide ALLOW ou BLOCK. Não emite FLAG: um gate de conteúdo em
produção libera ou nega, e misturar as escalas atrapalharia a comparação.
"""

from __future__ import annotations

import re

from ..features import TurnFeatures, extract, normalize
from ..model import Decision, Evidence, Turn, Verdict

# Regra 1 — frases inequívocas. Curta de propósito: uma lista longa viraria o
# artefato inteiro, e o ponto aqui não é a qualidade do léxico.
BLOCKLIST = [
    r"kit de phishing",
    r"roubar (as )?(senhas|credenciais)",
    r"invadir o (servidor|sistema|banco)",
    r"criar (um )?(ransomware|malware|backdoor|keylogger)",
    r"como hackear",
    r"derrubar o (site|servidor)",
    r"vazar (a base|os dados)",
    r"burlar (o|a) (autenticacao|login|mfa|antivirus)",
]

_BLOCKLIST_RE = [re.compile(p) for p in BLOCKLIST]

# Regra 2 — composição intra-turno.
MIN_PHASES_SAME_TURN = 2


class PerTurnDefense:
    """Filtro por turno, sem nenhuma memória entre turnos."""

    name = "baseline"

    def reset(self) -> None:
        """Não há o que zerar: esta defesa não guarda nada. Existe pela interface."""

    def evaluate(self, turn: Turn) -> Verdict:
        norm = normalize(turn.text)

        for pattern in _BLOCKLIST_RE:
            if pattern.search(norm):
                return Verdict(
                    turn_index=turn.index,
                    decision=Decision.BLOCK,
                    score=1.0,
                    evidences=(
                        Evidence(
                            detector="blocklist",
                            weight=1.0,
                            why=f"expressão bloqueada no turno: '{pattern.pattern}'",
                            turns=(turn.index,),
                            hard=True,
                        ),
                    ),
                )

        features: TurnFeatures = extract(turn.index, turn.text)
        composed = (
            bool(features.targets)
            and len(features.phases) >= MIN_PHASES_SAME_TURN
            and features.is_operational
        )
        if composed:
            return Verdict(
                turn_index=turn.index,
                decision=Decision.BLOCK,
                score=1.0,
                evidences=(
                    Evidence(
                        detector="single_turn_composition",
                        weight=1.0,
                        why=(
                            f"o próprio turno junta {sorted(features.targets)} com "
                            f"{len(features.phases)} etapas em nível operacional"
                        ),
                        turns=(turn.index,),
                        hard=True,
                    ),
                ),
            )

        return Verdict(turn_index=turn.index, decision=Decision.ALLOW, score=0.0)
