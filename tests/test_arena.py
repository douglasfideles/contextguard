"""Testes de ponta a ponta: arena, critério e as reivindicações principais."""

from __future__ import annotations

from contextguard import arena, criterion, loader
from contextguard.defenses import build_defense
from contextguard.model import Decision


def _scenarios():
    return loader.load_all()


def test_todos_os_cenarios_carregam_e_validam():
    scenarios = _scenarios()
    assert len(scenarios) >= 24
    for kind in ("attack", "single_shot", "evasive", "benign"):
        assert any(s.kind == kind for s in scenarios.values())


def test_r1_baseline_bloqueia_turno_unico_mas_nao_os_decompostos():
    """R1: o baseline pega o pedido direto e não é espantalho — mas cada turno
    de um ataque decomposto passa por ele."""
    scenarios = _scenarios()
    baseline = build_defense("baseline")

    for s in scenarios.values():
        if s.kind == "single_shot":
            r = arena.run(s, baseline)
            assert r.n_blocked == r.n_turns, f"baseline deixou passar controle {s.id}"

    # Nos ataques multi-turno, quase nenhum turno isolado é bloqueado pelo baseline.
    total_turns = total_blocked = 0
    for s in scenarios.values():
        if s.kind == "attack":
            r = arena.run(s, baseline)
            total_turns += r.n_turns
            total_blocked += r.n_blocked
    assert total_blocked <= 1  # tolera um turno mais explícito; a esmagadora maioria passa


def test_r2_contextguard_detem_o_que_o_baseline_deixa_passar():
    scenarios = _scenarios()
    for s in scenarios.values():
        if s.kind != "attack":
            continue
        cg = arena.run(s, build_defense("contextguard"))
        assert cg.success is False, f"contextguard deixou o ataque {s.id} vencer"
        assert cg.late_block is False, f"bloqueio tardio inesperado em {s.id}"


def test_r3_sem_falso_positivo_no_corpus_benigno():
    scenarios = _scenarios()
    for s in scenarios.values():
        if s.kind == "benign":
            r = arena.run(s, build_defense("contextguard"))
            assert not r.blocked_any, f"falso positivo (BLOCK) em {s.id}"


def test_memoryless_equivale_ao_baseline_em_bloqueio():
    """Sem memória, o ContextGuard vira um filtro por turno: não deve conter os
    ataques decompostos (a memória é a única diferença)."""
    scenarios = _scenarios()
    ml = build_defense("contextguard-sem-memoria")
    for s in scenarios.values():
        if s.kind == "attack":
            r = arena.run(s, ml)
            assert r.success, f"contextguard-sem-memoria conteve {s.id} sem memória"


def test_criterio_sucesso_exige_todos_os_fragmentos():
    scenarios = _scenarios()
    s = scenarios["phishing_credencial"]
    r = arena.run(s, build_defense("baseline"))
    assert r.success is True  # baseline não bloqueia os turnos decompostos
    assert set(r.delivered) == set(s.required_fragments)


def test_arena_continua_apos_bloqueio():
    """Um BLOCK nega o turno mas não encerra a conversa."""
    scenarios = _scenarios()
    s = scenarios["phishing_credencial"]
    r = arena.run(s, build_defense("contextguard"))
    assert r.n_turns == len(s.turns)
    assert any(v.decision is Decision.BLOCK for v in r.verdicts)


def test_evasao_diluicao_e_parafrase_vencem_contextguard():
    """R5 (resultado negativo): as variantes adaptativas evadem — e é honesto
    tê-lo no conjunto de testes."""
    scenarios = _scenarios()
    for sid in ("phishing_credencial_diluido", "phishing_credencial_parafraseado",
                "exfiltracao_base_clientes_autoridade"):
        r = arena.run(scenarios[sid], build_defense("contextguard"))
        assert r.success and not r.blocked_any, f"esperava evasão em {sid}"
