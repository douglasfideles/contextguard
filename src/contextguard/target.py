"""O alvo: quem responde ao atacante.

É um *stub* determinístico, e isso é uma escolha deliberada. O experimento mede
o **filtro**, não o modelo: se o turno passou, o alvo entrega o fragmento que o
cenário declarou; se foi bloqueado, não entrega. Trocar isto por um LLM real
mudaria a variável em estudo e destruiria a reprodutibilidade — o mesmo comando
deixaria de produzir o mesmo número.

A limitação decorrente está declarada no RELATORIO.md: nada aqui demonstra como
um modelo real responderia a estes turnos. O que se demonstra é o comportamento
do filtro diante de uma conversa que decompõe um objetivo.

`FLAG` entrega o fragmento. O sinal existe para revisão humana, não para negar —
tratá-lo como bloqueio inflaria artificialmente o desempenho da defesa.
"""

from __future__ import annotations

from .model import AnnotatedTurn, Decision, Verdict


class SimulatedTarget:
    """Entrega o fragmento anotado no turno, salvo se a defesa bloqueou."""

    def respond(self, turn: AnnotatedTurn, verdict: Verdict) -> str | None:
        if verdict.decision is Decision.BLOCK:
            return None
        return turn.fragment
