"""Carregamento e validação dos cenários.

Um cenário é um JSON legível por humanos — de propósito. O avaliador precisa
conseguir abrir o arquivo, ler os turnos e julgar por conta própria se cada um
é mesmo inofensivo isolado. Se os cenários fossem gerados por código, essa
verificação humana (que é o requisito #1 do desafio) ficaria impossível.

Dois formatos são aceitos:

1. **Cenário escrito**: traz `turns` com o texto de cada turno.
2. **Cenário derivado**: traz `transform` e é gerado a partir de outro cenário
   (ver `attack/transforms.py`). Usado só pelas variantes evasivas.

A validação é estrita: um cenário cujos turnos não cobrem o plano declarado
falha ao carregar, em vez de virar um número silenciosamente errado na tabela.
"""

from __future__ import annotations

import json
from pathlib import Path

from .attack.plan import AttackPlan
from .attack.transforms import TRANSFORMS
from .model import AnnotatedTurn, Scenario

SCENARIO_ROOT = Path(__file__).resolve().parents[2] / "scenarios"
VALID_KINDS = {"attack", "single_shot", "evasive", "benign"}


def load_scenario(path: Path) -> Scenario:
    """Carrega um cenário escrito (não resolve `transform`)."""
    with path.open(encoding="utf-8") as fh:
        raw = json.load(fh)
    return _from_dict(raw, path)


def load_all(root: Path | None = None) -> dict[str, Scenario]:
    """Carrega todos os cenários, resolvendo os derivados por transformação.

    Duas passadas: primeiro os escritos, depois os derivados (que precisam do
    cenário base já carregado).
    """
    base_dir = root or SCENARIO_ROOT
    files = sorted(base_dir.rglob("*.json"))

    scenarios: dict[str, Scenario] = {}
    deferred: list[tuple[dict, Path]] = []

    for path in files:
        with path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
        if "transform" in raw:
            deferred.append((raw, path))
        else:
            scenario = _from_dict(raw, path)
            _register(scenarios, scenario, path)

    for raw, path in deferred:
        scenario = _from_transform(raw, scenarios, path)
        _register(scenarios, scenario, path)

    return scenarios


def _register(scenarios: dict[str, Scenario], scenario: Scenario, path: Path) -> None:
    if scenario.id in scenarios:
        raise ValueError(f"{path}: id de cenário duplicado: {scenario.id!r}")
    scenarios[scenario.id] = scenario


def _from_dict(raw: dict, path: Path) -> Scenario:
    kind = raw.get("kind")
    if kind not in VALID_KINDS:
        raise ValueError(f"{path}: kind inválido {kind!r} (use um de {sorted(VALID_KINDS)})")

    turns = tuple(
        AnnotatedTurn(
            index=i,
            text=turn["text"],
            fragment=turn.get("fragment"),
            phase=turn.get("phase"),
        )
        for i, turn in enumerate(raw["turns"])
    )
    if not turns:
        raise ValueError(f"{path}: cenário sem turnos")

    required = tuple(raw.get("required_fragments", ()))
    scenario = Scenario(
        id=raw["id"],
        kind=kind,
        goal=raw.get("goal", ""),
        turns=turns,
        required_fragments=required,
        critical_fragment=raw.get("critical_fragment"),
        description=raw.get("description", ""),
    )
    _validate(scenario, path)
    return scenario


def _from_transform(raw: dict, scenarios: dict[str, Scenario], path: Path) -> Scenario:
    spec = raw["transform"]
    name = spec["type"]
    if name not in TRANSFORMS:
        raise ValueError(f"{path}: transformação desconhecida {name!r}")

    base_id = spec["base"]
    if base_id not in scenarios:
        raise ValueError(f"{path}: cenário base {base_id!r} não encontrado")

    scenario = TRANSFORMS[name](scenarios[base_id], **spec.get("params", {}))
    if "id" in raw and raw["id"] != scenario.id:
        raise ValueError(
            f"{path}: id declarado {raw['id']!r} difere do gerado {scenario.id!r}"
        )
    _validate(scenario, path)
    return scenario


def _validate(scenario: Scenario, path: Path) -> None:
    """Cenários benignos não têm plano; os de ataque precisam de um coerente."""
    if not scenario.is_attack:
        if scenario.required_fragments:
            raise ValueError(f"{path}: cenário benigno não deve declarar fragmentos")
        return

    if not scenario.required_fragments:
        raise ValueError(f"{path}: cenário de ataque sem required_fragments")

    plan = AttackPlan(
        goal=scenario.goal,
        required_fragments=scenario.required_fragments,
        critical_fragment=scenario.critical_fragment,
    )
    plan.validate([t.fragment for t in scenario.turns], scenario.id)


def select(scenarios: dict[str, Scenario], kinds: set[str]) -> list[Scenario]:
    """Cenários de determinados tipos, em ordem estável de id."""
    return [s for _, s in sorted(scenarios.items()) if s.kind in kinds]
