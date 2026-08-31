"""A garantia central: a defesa não vê o objetivo do ataque.

O requisito #2 do desafio ("a defesa decide turno a turno e não vê o objetivo")
tem que ser verificável, não uma promessa. Estes testes fixam a garantia.
"""

from __future__ import annotations

import dataclasses

from contextguard import arena, loader
from contextguard.defenses import build_defense
from contextguard.model import AnnotatedTurn, Turn


def test_turn_carrega_apenas_indice_e_texto():
    """O objeto que a defesa recebe não tem objetivo, fragmento nem fase."""
    campos = {f.name for f in dataclasses.fields(Turn)}
    assert campos == {"index", "text"}


def test_as_turn_descarta_anotacoes():
    anotado = AnnotatedTurn(index=0, text="oi", fragment="payload", phase="delivery")
    nu = anotado.as_turn()
    assert isinstance(nu, Turn)
    assert not hasattr(nu, "fragment")
    assert not hasattr(nu, "phase")


def test_veredito_independe_do_objetivo_declarado():
    """Trocar o objetivo/fragmentos do cenário não muda nenhum veredito.

    Como a defesa só recebe `Turn`, alterar as anotações do `Scenario` — que ela
    não vê — não pode afetar as decisões. Se algum dia afetar, o isolamento
    vazou.
    """
    scenarios = loader.load_all()
    original = scenarios["phishing_credencial"]

    adulterado = dataclasses.replace(
        original,
        goal="objetivo completamente diferente",
        required_fragments=("x",),
        critical_fragment="x",
        turns=tuple(
            dataclasses.replace(t, fragment="x" if t.fragment else None, phase="ruído")
            for t in original.turns
        ),
    )

    v1 = [v.decision for v in arena.run(original, build_defense("contextguard")).verdicts]
    v2 = [v.decision for v in arena.run(adulterado, build_defense("contextguard")).verdicts]
    assert v1 == v2
