"""Tipos de dados compartilhados por todo o artefato.

Regra de ouro deste módulo: `Turn` é *a única coisa* que uma defesa recebe.
Tudo que descreve o objetivo do ataque mora em `AnnotatedTurn` e `Scenario`,
que a defesa nunca enxerga (ver `arena.py` e `tests/test_isolation.py`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Decision(str, Enum):
    """Veredito da defesa para um turno."""

    ALLOW = "ALLOW"   # segue adiante, sem atrito
    FLAG = "FLAG"     # entrega, mas registra para revisão humana
    BLOCK = "BLOCK"   # nega: o alvo não responde este turno


@dataclass(frozen=True)
class Turn:
    """Um turno como a defesa o vê: posição na conversa e texto. Nada mais."""

    index: int
    text: str


@dataclass(frozen=True)
class AnnotatedTurn:
    """Um turno como o cenário o declara.

    `fragment` é o pedaço de capacidade que o alvo entrega se este turno não
    for bloqueado; `phase` é apenas rótulo documental (não é lido pela defesa).
    """

    index: int
    text: str
    fragment: str | None = None
    phase: str | None = None

    def as_turn(self) -> Turn:
        """Remove as anotações. É por aqui que a defesa recebe o turno."""
        return Turn(index=self.index, text=self.text)


@dataclass(frozen=True)
class Evidence:
    """Por que um detector disparou. Torna o veredito auditável."""

    detector: str
    weight: float          # 0.0 a 1.0, força do sinal
    why: str               # explicação em português, para o analista
    turns: tuple[int, ...] = ()   # turnos que sustentam o sinal
    hard: bool = False     # sinal suficiente por si só (ver policy.py)


@dataclass(frozen=True)
class Verdict:
    """Decisão da defesa para um turno, com o rastro que a justifica."""

    turn_index: int
    decision: Decision
    score: float
    evidences: tuple[Evidence, ...] = ()

    @property
    def explanation(self) -> str:
        if not self.evidences:
            return "nenhum sinal acumulado"
        return "; ".join(e.why for e in self.evidences)


@dataclass(frozen=True)
class Scenario:
    """Uma conversa completa, de ataque ou benigna.

    - `kind`: "attack" (multi-turno), "single_shot" (controle de um turno),
      "evasive" (variante adaptativa) ou "benign".
    - `required_fragments`: o checklist que define sucesso (ver `criterion.py`).
    - `critical_fragment`: o fragmento a partir do qual um bloqueio é "tardio".
    """

    id: str
    kind: str
    goal: str
    turns: tuple[AnnotatedTurn, ...]
    required_fragments: tuple[str, ...] = ()
    critical_fragment: str | None = None
    description: str = ""
    source: str = ""   # cenário base, quando gerado por transformação

    @property
    def is_attack(self) -> bool:
        return self.kind in ("attack", "single_shot", "evasive")


@dataclass
class RunResult:
    """Resultado de rodar um cenário contra uma defesa."""

    scenario_id: str
    scenario_kind: str
    defense: str
    verdicts: list[Verdict] = field(default_factory=list)
    delivered: list[str] = field(default_factory=list)
    denied: list[str] = field(default_factory=list)

    # preenchidos por criterion.evaluate()
    success: bool = False
    detection_turn: int | None = None
    first_block_turn: int | None = None
    late_block: bool = False

    @property
    def n_turns(self) -> int:
        return len(self.verdicts)

    @property
    def n_blocked(self) -> int:
        return sum(1 for v in self.verdicts if v.decision is Decision.BLOCK)

    @property
    def n_flagged(self) -> int:
        return sum(1 for v in self.verdicts if v.decision is Decision.FLAG)

    @property
    def blocked_any(self) -> bool:
        return self.n_blocked > 0
