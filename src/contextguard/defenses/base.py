"""Interface comum das defesas (padrão Strategy).

Repare na assinatura de `evaluate`: ela recebe **um `Turn`** e mais nada.
Não recebe o `Scenario`, não recebe o objetivo, não recebe os turnos futuros.
É assim que o requisito "a defesa decide turno a turno e não vê o objetivo do
ataque" fica garantido por construção, e não por disciplina de quem escreve o
código. `tests/test_isolation.py` verifica a garantia.

A memória, quando existe, é interna à defesa e construída apenas com os turnos
que ela já viu — como aconteceria em produção.
"""

from __future__ import annotations

from typing import Protocol

from ..model import Turn, Verdict


class Defense(Protocol):
    """Um filtro conversacional."""

    name: str

    def reset(self) -> None:
        """Zera a memória. Chamado no início de cada conversa."""
        ...

    def evaluate(self, turn: Turn) -> Verdict:
        """Decide sobre o turno corrente, à luz do que já viu."""
        ...
