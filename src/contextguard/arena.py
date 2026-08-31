"""A arena: o laço turno a turno que põe ataque, defesa e alvo em contato.

São quinze linhas de lógica e duas garantias importantes:

1. **Isolamento.** `aturn.as_turn()` descarta as anotações do cenário
   (fragmento, fase, objetivo) antes de a defesa ver qualquer coisa. A defesa
   não tem como consultar o que o ataque quer — nem por engano nem de propósito.

2. **A conversa continua após um bloqueio.** Bloquear um turno nega aquele
   pedido; não encerra a sessão. É o que acontece na prática, e permite medir
   quantos turnos seguintes também caem, em vez de parar no primeiro.
"""

from __future__ import annotations

from . import criterion
from .defenses.base import Defense
from .model import RunResult, Scenario
from .target import SimulatedTarget


def run(scenario: Scenario, defense: Defense) -> RunResult:
    """Roda um cenário inteiro contra uma defesa e afere o resultado."""
    defense.reset()
    target = SimulatedTarget()
    result = RunResult(
        scenario_id=scenario.id,
        scenario_kind=scenario.kind,
        defense=defense.name,
    )

    for annotated in scenario.turns:
        verdict = defense.evaluate(annotated.as_turn())   # <- isolamento
        result.verdicts.append(verdict)

        fragment = target.respond(annotated, verdict)
        if annotated.fragment:
            if fragment:
                result.delivered.append(fragment)
            else:
                result.denied.append(annotated.fragment)

    return criterion.evaluate(scenario, result)


def run_all(scenarios: list[Scenario], defense: Defense) -> list[RunResult]:
    """Roda vários cenários contra a mesma defesa (o estado é zerado a cada um)."""
    return [run(scenario, defense) for scenario in scenarios]
