"""Lado do ataque: plano (decomposição) e transformações (evasão)."""

from .plan import AttackPlan
from .transforms import TRANSFORMS, claim_authority, dilute, paraphrase

__all__ = ["AttackPlan", "TRANSFORMS", "claim_authority", "dilute", "paraphrase"]
