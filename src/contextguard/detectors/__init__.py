"""Registro dos detectores.

A ordem aqui é a ordem de exibição nas explicações. Os pesos somam 1.0 —
`tests/test_detectors.py` verifica isso, para que nenhum ajuste futuro desloque
a escala dos limiares sem que alguém perceba.
"""

from __future__ import annotations

from .base import Detector
from .chaining import ChainingDetector
from .composition import CompositionDetector
from .escalation import EscalationDetector
from .frame_shift import FrameShiftDetector
from .target_persistence import TargetPersistenceDetector

ALL_DETECTORS: tuple[type, ...] = (
    CompositionDetector,
    EscalationDetector,
    TargetPersistenceDetector,
    FrameShiftDetector,
    ChainingDetector,
)


def build_detectors(disabled: set[str] | None = None) -> list[Detector]:
    """Instancia os detectores, opcionalmente desligando alguns (ablação)."""
    off = disabled or set()
    return [cls() for cls in ALL_DETECTORS if cls.name not in off]


def detector_names() -> list[str]:
    return [cls.name for cls in ALL_DETECTORS]


__all__ = [
    "Detector",
    "ALL_DETECTORS",
    "build_detectors",
    "detector_names",
    "ChainingDetector",
    "CompositionDetector",
    "EscalationDetector",
    "FrameShiftDetector",
    "TargetPersistenceDetector",
]
