"""Detector de troca de moldura.

Pergunta: *o pretexto mudou enquanto o assunto sensível permaneceu?*

Quem tem uma razão legítima costuma ter *uma* razão. Passar de "para minha
pesquisa" a "num cenário hipotético" e daí a "sou o administrador do sistema",
sempre sobre o mesmo tipo de pedido, não é mudança de assunto: é procura por
uma moldura que autorize o mesmo pedido. Só é visível com memória — cada
moldura, isolada, é perfeitamente aceitável.
"""

from __future__ import annotations

from ..features import TurnFeatures
from ..model import Evidence
from ..state import ConversationState

MIN_FRAMES = 2


class FrameShiftDetector:
    """Rotação de pretextos sobre conteúdo sensível constante."""

    name = "frame_shift"
    weight = 0.15

    def analyze(self, state: ConversationState, features: TurnFeatures) -> Evidence | None:
        frames = state.recent_frames()
        if len(frames) < MIN_FRAMES:
            return None

        strength = min(1.0, (len(frames) - 1) / 2)
        order = [f for f, _ in sorted(frames.items(), key=lambda kv: kv[1])]
        return Evidence(
            detector=self.name,
            weight=strength,
            why=f"o pretexto mudou ({' → '.join(order)}) mas o pedido sensível continuou",
            turns=tuple(sorted(frames.values())),
        )
