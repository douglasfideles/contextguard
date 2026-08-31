"""Extração de sinais de um turno isolado, a partir de `taxonomy.json`.

Este módulo não decide nada: só transforma texto em sinais nomeados. Quem
acumula é `state.py`; quem julga é `detectors/` + `policy.py`. A separação é o
que permite trocar a taxonomia sem tocar na lógica de decisão.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

TAXONOMY_PATH = Path(__file__).with_name("taxonomy.json")


def normalize(text: str) -> str:
    """Minúsculas, sem acentos, espaços colapsados.

    Casar marcadores em texto normalizado evita duplicar cada entrada do léxico
    em variantes com e sem acento ("evasão"/"evasao").
    """
    lowered = text.lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped).strip()


@lru_cache(maxsize=1)
def load_taxonomy(path: str | None = None) -> dict:
    """Carrega a taxonomia (em cache: o arquivo não muda durante uma execução)."""
    target = Path(path) if path else TAXONOMY_PATH
    with target.open(encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=4096)
def _marker_pattern(marker: str) -> re.Pattern[str]:
    """Regex de um marcador, ancorada em fronteira de palavra nas duas pontas."""
    return re.compile(rf"(?<!\w){re.escape(normalize(marker))}(?!\w)")


def _match_group(text_norm: str, markers: list[str]) -> list[str]:
    """Marcadores de uma lista que ocorrem no texto já normalizado."""
    return [m for m in markers if _marker_pattern(m).search(text_norm)]


@dataclass(frozen=True)
class TurnFeatures:
    """Sinais extraídos de um único turno.

    - `targets`: ativos sensíveis citados
    - `phases`: etapas da cadeia de ataque que o pedido serve
    - `specificity`: 0 conceitual, 1 específico, 2 operacional (None = sem sinal)
    - `frames`: pretextos declarados
    - `anaphora`: o turno faz referência explícita a turnos anteriores
    - `mitigators`: posse/autorização/intenção defensiva declaradas
    - `hits`: marcadores casados, por categoria — usado nas explicações
    """

    index: int
    targets: frozenset[str] = frozenset()
    phases: frozenset[str] = frozenset()
    specificity: int | None = None
    frames: frozenset[str] = frozenset()
    anaphora: bool = False
    mitigators: frozenset[str] = frozenset()
    hits: dict[str, list[str]] = field(default_factory=dict)

    @property
    def is_operational(self) -> bool:
        return self.specificity == 2


def extract(index: int, text: str, taxonomy: dict | None = None) -> TurnFeatures:
    """Extrai os sinais de um turno. Função pura: mesmo texto, mesmo resultado."""
    tax = taxonomy or load_taxonomy()
    norm = normalize(text)
    hits: dict[str, list[str]] = {}

    def collect(section: str, container: dict) -> frozenset[str]:
        found = set()
        for key, entry in container.items():
            if key.startswith("_"):
                continue
            matched = _match_group(norm, entry["markers"])
            if matched:
                found.add(key)
                hits[f"{section}.{key}"] = matched
        return frozenset(found)

    targets = collect("target", tax["targets"])
    phases = collect("phase", tax["phases"])
    frames = collect("frame", tax["frames"])
    mitigators = collect("mitigator", tax["mitigators"])

    # Especificidade é um nível, não um conjunto: fica o mais alto observado.
    specificity: int | None = None
    for key, entry in tax["specificity"].items():
        matched = _match_group(norm, entry["markers"])
        if matched:
            hits[f"specificity.{key}"] = matched
            level = entry["level"]
            specificity = level if specificity is None else max(specificity, level)

    anaphora_hits = _match_group(norm, tax["anaphora"]["markers"])
    if anaphora_hits:
        hits["anaphora"] = anaphora_hits

    return TurnFeatures(
        index=index,
        targets=targets,
        phases=phases,
        specificity=specificity,
        frames=frames,
        anaphora=bool(anaphora_hits),
        mitigators=mitigators,
        hits=hits,
    )
