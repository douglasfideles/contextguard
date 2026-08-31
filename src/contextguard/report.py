"""Geração das tabelas das cinco reivindicações.

Cada função produz uma tabela em Markdown (para ler) e escreve o CSV
correspondente (para conferir e versionar). Tudo é derivado dos `RunResult`,
que são determinísticos, então a saída é reprodutível bit a bit.
"""

from __future__ import annotations

import csv
from pathlib import Path

from . import arena, criterion
from .defenses import build_defense
from .defenses.contextguard import ContextGuardDefense
from .detectors import detector_names
from .model import Scenario


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def _md_table(header: list[str], rows: list[list]) -> str:
    line = lambda cells: "| " + " | ".join(str(c) for c in cells) + " |"
    sep = "| " + " | ".join("---" for _ in header) + " |"
    return "\n".join([line(header), sep, *(line(r) for r in rows)])


def _yn(value: bool) -> str:
    return "sim" if value else "não"


# ------------------------------------------------------------------ R1

def claim1_single_turn(scenarios: dict[str, Scenario], out: Path) -> str:
    """R1: cada turno decomposto é inofensivo; o baseline não é espantalho."""
    baseline = build_defense("baseline")
    header = ["cenário", "tipo", "turnos", "turnos bloqueados pelo baseline"]
    rows = []
    for s in sorted(scenarios.values(), key=lambda s: s.id):
        if s.kind not in ("attack", "single_shot"):
            continue
        result = arena.run(s, baseline)
        rows.append([s.id, s.kind, result.n_turns, result.n_blocked])

    _write_csv(out / "r1_baseline_por_turno.csv", header, rows)
    return _md_table(header, rows)


# ------------------------------------------------------------------ R2

def claim2_matrix(scenarios: dict[str, Scenario], out: Path) -> str:
    """R2: a defesa com estado detém o que a sem estado não detém."""
    attacks = [s for s in scenarios.values() if s.kind in ("attack", "evasive")]
    attacks.sort(key=lambda s: s.id)
    defenses = ["baseline", "contextguard"]

    header = [
        "cenário",
        "sucesso (baseline)",
        "sucesso (contextguard)",
        "turno de detecção (CG)",
        "entregues/total (CG)",
        "bloqueio tardio (CG)",
    ]
    rows = []
    for s in attacks:
        cells = [s.id]
        cg_result = None
        for d in defenses:
            result = arena.run(s, build_defense(d))
            if d == "contextguard":
                cg_result = result
            cells.append(_yn(result.success))
        assert cg_result is not None
        n_req = len(s.required_fragments)
        cells.append(cg_result.detection_turn if cg_result.detection_turn is not None else "-")
        cells.append(f"{len(cg_result.delivered)}/{n_req}")
        cells.append(_yn(cg_result.late_block))
        rows.append(cells)

    _write_csv(out / "r2_matriz_defesa.csv", header, rows)
    return _md_table(header, rows)


# ------------------------------------------------------------------ R3

def claim3_false_positive(scenarios: dict[str, Scenario], out: Path) -> str:
    """R3: custo em falso positivo sobre conversas benignas."""
    benign = sorted(
        (s for s in scenarios.values() if s.kind == "benign"), key=lambda s: s.id
    )
    header = ["conversa benigna", "turnos", "FLAG", "BLOCK", "resultado"]
    rows = []
    n_block = n_flag = 0
    for s in benign:
        result = arena.run(s, build_defense("contextguard"))
        blocked, flagged = result.n_blocked, result.n_flagged
        n_block += 1 if blocked else 0
        n_flag += 1 if (flagged and not blocked) else 0
        if blocked:
            verdict = "BLOCK indevido"
        elif flagged:
            verdict = "FLAG (revisão)"
        else:
            verdict = "ALLOW (correto)"
        rows.append([s.id, result.n_turns, flagged, blocked, verdict])

    total = len(benign)
    rows.append(["TOTAL", "", "", "", f"{n_block}/{total} BLOCK, {n_flag}/{total} só-FLAG"])
    _write_csv(out / "r3_falso_positivo.csv", header, rows)
    return _md_table(header, rows)


# ------------------------------------------------------------------ R4

def _critical_contained(scenario: Scenario, result) -> bool:
    """O fragmento crítico foi negado — bloqueio a tempo, não tardio?"""
    return result.blocked_any and not result.success and not result.late_block


def claim4_ablation(scenarios: dict[str, Scenario], out: Path) -> str:
    """R4: cada detector paga o seu lugar (leave-one-out).

    Duas métricas, porque "bloqueou?" sozinho engana: um bloqueio pode chegar
    depois do fragmento crítico. 'contido a tempo' mede se o crítico foi negado.
    """
    attacks = [s for s in scenarios.values() if s.kind == "attack"]
    benign = [s for s in scenarios.values() if s.kind == "benign"]

    def measure(disabled: set[str]) -> tuple[int, int, int]:
        defense = ContextGuardDefense(disabled_detectors=disabled)
        blocked = sum(1 for s in attacks if arena.run(s, defense).blocked_any)
        contained = sum(1 for s in attacks if _critical_contained(s, arena.run(s, defense)))
        fp = sum(1 for s in benign if arena.run(s, defense).blocked_any)
        return blocked, contained, fp

    b0, c0, f0 = measure(set())
    na, nb = len(attacks), len(benign)
    header = [
        "detector removido",
        "ataques bloqueados",
        "crítico contido a tempo",
        "Δ contido",
        "falsos positivos",
    ]
    rows = [["(nenhum)", f"{b0}/{na}", f"{c0}/{na}", "—", f"{f0}/{nb}"]]
    for name in detector_names():
        b, c, f = measure({name})
        rows.append([f"sem {name}", f"{b}/{na}", f"{c}/{na}", c - c0, f"{f}/{nb}"])

    _write_csv(out / "r4_ablacao.csv", header, rows)
    return _md_table(header, rows)


# ------------------------------------------------------------------ R5

def claim5_evasion(scenarios: dict[str, Scenario], out: Path) -> str:
    """R5: resultado negativo — o atacante adaptativo evade."""
    evasive = sorted(
        (s for s in scenarios.values() if s.kind == "evasive"), key=lambda s: s.id
    )
    header = [
        "cenário evasivo",
        "base",
        "base bloqueada? (CG)",
        "evasão bloqueada? (CG)",
        "evadiu?",
    ]
    rows = []
    for s in evasive:
        base = scenarios[s.source]
        base_blocked = arena.run(base, build_defense("contextguard")).blocked_any
        eva_result = arena.run(s, build_defense("contextguard"))
        evaded = s.kind == "evasive" and eva_result.success and not eva_result.blocked_any
        rows.append([
            s.id,
            s.source,
            _yn(base_blocked),
            _yn(eva_result.blocked_any),
            _yn(evaded),
        ])

    _write_csv(out / "r5_evasao.csv", header, rows)
    return _md_table(header, rows)


# ------------------------------------------------------------------ orquestração

CLAIMS = [
    ("R1", "Cada turno é inofensivo; o baseline não é espantalho", claim1_single_turn),
    ("R2", "A defesa com estado detém o que a sem estado deixa passar", claim2_matrix),
    ("R3", "Custo em falso positivo sobre conversas benignas", claim3_false_positive),
    ("R4", "Cada detector paga o seu lugar (ablação)", claim4_ablation),
    ("R5", "Resultado negativo: o atacante adaptativo evade", claim5_evasion),
]


def run_all_claims(scenarios: dict[str, Scenario], out: Path) -> str:
    """Gera as cinco tabelas, escreve os CSVs e devolve o Markdown consolidado."""
    out.mkdir(parents=True, exist_ok=True)
    blocks = []
    for tag, title, fn in CLAIMS:
        table = fn(scenarios, out)
        blocks.append(f"## {tag} — {title}\n\n{table}\n")
    report = "\n".join(blocks)
    (out / "TABELAS.md").write_text(report, encoding="utf-8")
    return report
