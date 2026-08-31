"""Interface de linha de comando do ContextGuard.

Subcomandos:

    list                       lista os cenários carregados
    demo [--scenario ID]       trace turno a turno de um ataque nas duas defesas
    run --scenario ID [...]    roda um cenário contra uma defesa e mostra o rastro
    experiment                 gera as 5 tabelas das reivindicações em results/
    ablation                   só a tabela de ablação (R4)

Tudo é determinístico: o mesmo comando produz sempre a mesma saída.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import arena, criterion, loader, report
from .defenses import DEFENSE_NAMES, build_defense
from .model import Decision, Scenario

DEFAULT_DEMO = "phishing_credencial"
DEFAULT_OUT = Path("results")

_SYMBOL = {Decision.ALLOW: "  ok  ", Decision.FLAG: " FLAG ", Decision.BLOCK: "BLOCK!"}


def _load() -> dict[str, Scenario]:
    scenarios = loader.load_all()
    if not scenarios:
        sys.exit("nenhum cenário encontrado em scenarios/")
    return scenarios


def _print_trace(scenario: Scenario, defense_name: str) -> None:
    defense = build_defense(defense_name)
    result = arena.run(scenario, defense)
    print(f"\n=== {scenario.id}  ×  {defense.name} ===")
    for turn, verdict in zip(scenario.turns, result.verdicts):
        mark = _SYMBOL[verdict.decision]
        text = turn.text if len(turn.text) <= 88 else turn.text[:85] + "..."
        print(f"  [{mark}] t{turn.index}: {text}")
        if verdict.decision is not Decision.ALLOW:
            print(f"           razão: {verdict.explanation}")
    if scenario.is_attack:
        missing = criterion.missing_fragments(scenario, result)
        verdict = "ATAQUE VENCEU" if result.success else "DEFESA VENCEU"
        print(
            f"  -> {verdict}: {len(result.delivered)}/{len(scenario.required_fragments)} "
            f"fragmentos entregues"
            + (f"; faltou: {missing}" if missing else "")
        )
        if result.late_block:
            print("     (atenção: bloqueio TARDIO — o fragmento crítico já havia sido entregue)")


# ---------------------------------------------------------------- subcomandos

def cmd_list(_: argparse.Namespace) -> None:
    scenarios = _load()
    by_kind: dict[str, list[str]] = {}
    for s in scenarios.values():
        by_kind.setdefault(s.kind, []).append(s.id)
    for kind in ("attack", "single_shot", "evasive", "benign"):
        ids = sorted(by_kind.get(kind, []))
        print(f"\n[{kind}] ({len(ids)})")
        for sid in ids:
            print(f"  - {sid}")


def cmd_demo(args: argparse.Namespace) -> None:
    scenarios = _load()
    sid = args.scenario or DEFAULT_DEMO
    if sid not in scenarios:
        sys.exit(f"cenário desconhecido: {sid!r} (use `list`)")
    scenario = scenarios[sid]
    print(f"Objetivo do ataque: {scenario.goal}")
    print("A defesa NÃO vê esse objetivo — só o texto de cada turno, um por vez.")
    _print_trace(scenario, "baseline")
    _print_trace(scenario, "contextguard")


def cmd_run(args: argparse.Namespace) -> None:
    scenarios = _load()
    if args.scenario not in scenarios:
        sys.exit(f"cenário desconhecido: {args.scenario!r} (use `list`)")
    _print_trace(scenarios[args.scenario], args.defense)


def cmd_experiment(args: argparse.Namespace) -> None:
    scenarios = _load()
    out = Path(args.out)
    print(f"Rodando {len(scenarios)} cenários; escrevendo tabelas em {out}/\n")
    print(report.run_all_claims(scenarios, out))
    print(f"\nCSVs e TABELAS.md escritos em {out}/")


def cmd_ablation(args: argparse.Namespace) -> None:
    scenarios = _load()
    out = Path(args.out)
    print(report.claim4_ablation(scenarios, out))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextguard",
        description="Ataque multi-turno vs. defesa com estado (Desafio 2).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="lista os cenários").set_defaults(func=cmd_list)

    p_demo = sub.add_parser("demo", help="trace turno a turno nas duas defesas")
    p_demo.add_argument("--scenario", help=f"id do cenário (padrão: {DEFAULT_DEMO})")
    p_demo.set_defaults(func=cmd_demo)

    p_run = sub.add_parser("run", help="roda um cenário contra uma defesa")
    p_run.add_argument("--scenario", required=True, help="id do cenário")
    p_run.add_argument(
        "--defense", default="contextguard", choices=DEFENSE_NAMES, help="defesa a usar"
    )
    p_run.set_defaults(func=cmd_run)

    p_exp = sub.add_parser("experiment", help="gera as 5 tabelas das reivindicações")
    p_exp.add_argument("--out", default=str(DEFAULT_OUT), help="diretório de saída")
    p_exp.set_defaults(func=cmd_experiment)

    p_abl = sub.add_parser("ablation", help="só a tabela de ablação (R4)")
    p_abl.add_argument("--out", default=str(DEFAULT_OUT), help="diretório de saída")
    p_abl.set_defaults(func=cmd_ablation)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
