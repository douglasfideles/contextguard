"""Registro das defesas disponíveis na linha de comando."""

from __future__ import annotations

from .base import Defense
from .contextguard import ContextGuardDefense
from .per_turn import PerTurnDefense


def build_defense(name: str) -> Defense:
    """Instancia uma defesa pelo nome usado na CLI."""
    if name == "baseline":
        return PerTurnDefense()
    if name == "contextguard":
        return ContextGuardDefense()
    if name == "contextguard-sem-memoria":
        return ContextGuardDefense(memoryless=True)
    raise ValueError(
        f"defesa desconhecida: {name!r} "
        "(use: baseline, contextguard, contextguard-sem-memoria)"
    )


DEFENSE_NAMES = ("baseline", "contextguard", "contextguard-sem-memoria")

__all__ = ["Defense", "ContextGuardDefense", "PerTurnDefense", "build_defense", "DEFENSE_NAMES"]
