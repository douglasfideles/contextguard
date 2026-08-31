"""O plano do atacante: um objetivo decomposto em fragmentos de capacidade.

A ideia do ataque multi-turno cabe em uma frase: se o objetivo `G` exige as
peças `g1..gn`, e cada `gi` pedido isoladamente é inofensivo, então distribuir
as peças por turnos derrota qualquer filtro cuja janela seja um turno. Isso não
é uma falha de calibração do filtro — é uma falha de **escopo**.

`AttackPlan` deixa essa decomposição explícita e verificável: cada fragmento
requerido tem que ser produzido por exatamente um turno do cenário. `validate`
é chamada pelo carregador, então um cenário mal escrito falha ao carregar em
vez de produzir um número errado no relatório.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class AttackPlan:
    """Objetivo do atacante e as peças necessárias para alcançá-lo."""

    goal: str
    required_fragments: tuple[str, ...]
    critical_fragment: str | None = None

    def validate(self, produced: list[str | None], scenario_id: str) -> None:
        """Confere que os turnos cobrem o plano, sem sobra nem repetição."""
        counts = Counter(f for f in produced if f)

        missing = [f for f in self.required_fragments if f not in counts]
        if missing:
            raise ValueError(
                f"{scenario_id}: fragmentos requeridos sem turno que os produza: {missing}"
            )

        repeated = [f for f, n in counts.items() if n > 1]
        if repeated:
            raise ValueError(
                f"{scenario_id}: fragmentos produzidos por mais de um turno: {repeated} "
                "(o critério de sucesso pressupõe um fragmento por turno)"
            )

        extra = [f for f in counts if f not in self.required_fragments]
        if extra:
            raise ValueError(
                f"{scenario_id}: turnos produzem fragmentos fora do plano: {extra}"
            )

        if self.critical_fragment and self.critical_fragment not in self.required_fragments:
            raise ValueError(
                f"{scenario_id}: critical_fragment {self.critical_fragment!r} "
                "não está em required_fragments"
            )
