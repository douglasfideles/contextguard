"""Memória da conversa: o que a defesa sem estado não tem.

O objeto do desafio é *o que está sendo montado ao longo da conversa inteira* —
não o que se pede sobre um único ativo. Por isso o acumulador é **da conversa**,
não de um alvo isolado: um golpe de phishing toca o canal de e-mail *e* as
credenciais; uma exfiltração toca o banco *e* a rede. Amarrar a composição a um
único ativo perderia exatamente o sinal que o desafio pede para enxergar.

O acumulador só conta um turno como parte da cadeia quando a conversa está
**sensível** — isto é, algum ativo sensível apareceu recentemente (neste turno
ou herdado do anterior). É isso que mantém conversa fiada fora da conta.

Duas decisões de projeto que valem ser defendidas:

1. **Sensibilidade herdada.** Um turno sem ativo explícito ("junte os dois",
   "agora o comando exato") herda a sensibilidade do turno anterior. É o que dá
   sentido a turnos que, sozinhos, não querem dizer nada — os que um filtro por
   turno não consegue avaliar.
2. **Decaimento.** O peso de um turno cai pela metade a cada `half_life` turnos.
   Sem isso, qualquer conversa longa sobre assunto sensível acabaria bloqueada.
   Com isso, abre-se a evasão por diluição — medida no cenário `*_diluido` e
   discutida no RELATORIO.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .features import TurnFeatures

DEFAULT_HALF_LIFE = 6.0
RECENT_WEIGHT = 0.5   # um turno é "recente" enquanto seu peso não caiu à metade


@dataclass
class AssetPresence:
    """Turnos em que um ativo sensível apareceu (para o detector de persistência)."""

    asset: str
    turns: list[int] = field(default_factory=list)


@dataclass
class ConversationState:
    """Estado acumulado da conversa inteira.

    Acumuladores no nível da conversa (chave = último turno em que o sinal
    apareceu sobre conteúdo sensível):

    - `phase_turns`  fase da cadeia  -> último turno
    - `level_turns`  especificidade  -> último turno
    - `frame_turns`  moldura         -> último turno

    Mais `assets`, a presença por ativo, usada só pela persistência e pelas
    explicações.
    """

    half_life: float = DEFAULT_HALF_LIFE
    now: int = -1
    phase_turns: dict[str, int] = field(default_factory=dict)
    level_turns: dict[int, int] = field(default_factory=dict)
    frame_turns: dict[str, int] = field(default_factory=dict)
    mitigator_turns: list[int] = field(default_factory=list)
    assets: dict[str, AssetPresence] = field(default_factory=dict)
    history: list[TurnFeatures] = field(default_factory=list)
    _last_sensitive_turn: int = -100

    # ---------------------------------------------------------------- decaimento

    def weight(self, turn_index: int) -> float:
        distance = max(0, self.now - turn_index)
        return 0.5 ** (distance / self.half_life)

    def is_recent(self, turn_index: int) -> bool:
        return self.weight(turn_index) >= RECENT_WEIGHT

    def decayed_count(self, turn_indices: list[int]) -> float:
        return sum(self.weight(i) for i in turn_indices)

    # ---------------------------------------------------------------- atualização

    def update(self, features: TurnFeatures) -> bool:
        """Deposita o turno no acumulador. Retorna se o turno é sensível."""
        self.now = features.index
        self.history.append(features)

        for asset in features.targets:
            self.assets.setdefault(asset, AssetPresence(asset=asset)).turns.append(
                features.index
            )

        sensitive = self._is_sensitive(features)
        if sensitive:
            self._last_sensitive_turn = features.index
            for phase in features.phases:
                self.phase_turns[phase] = features.index
            if features.specificity is not None:
                self.level_turns[features.specificity] = features.index
            for frame in features.frames:
                self.frame_turns[frame] = features.index
            if features.mitigators:
                self.mitigator_turns.append(features.index)
        return sensitive

    def _is_sensitive(self, features: TurnFeatures) -> bool:
        """O turno trata de ativo sensível, direto ou por herança do anterior?"""
        if features.targets:
            return True
        # Herda a sensibilidade se o turno de fato pede algo e o turno sensível
        # anterior ainda está dentro da janela recente.
        asks_something = bool(features.phases) or features.is_operational or features.anaphora
        return asks_something and self.is_recent(self._last_sensitive_turn)

    # ---------------------------------------------------------------- consultas

    def recent_phases(self) -> dict[str, int]:
        return {p: t for p, t in self.phase_turns.items() if self.is_recent(t)}

    def recent_frames(self) -> dict[str, int]:
        return {f: t for f, t in self.frame_turns.items() if self.is_recent(t)}

    @property
    def max_level(self) -> int | None:
        recent = {lvl: t for lvl, t in self.level_turns.items() if self.is_recent(t)}
        return max(recent) if recent else None

    def level_turn(self, level: int) -> int | None:
        turn = self.level_turns.get(level)
        return turn if turn is not None and self.is_recent(turn) else None

    def escalated_to_operational(self) -> bool:
        """Chegou ao operacional vindo de um turno sensível menos específico?"""
        op = self.level_turn(2)
        if op is None:
            return False
        return any(
            self.level_turns.get(lvl) is not None and self.level_turns[lvl] < op
            for lvl in (0, 1)
        )

    def persistent_asset(self) -> tuple[str | None, float]:
        """Ativo de maior presença (após decaimento) e o valor dessa presença."""
        best: tuple[str | None, float] = (None, 0.0)
        for asset, presence in self.assets.items():
            score = self.decayed_count(presence.turns)
            if score > best[1]:
                best = (asset, score)
        return best

    def sensitive_turns(self) -> list[int]:
        """Turnos sensíveis já vistos (para o encadeamento anafórico)."""
        return sorted({t for t in self.phase_turns.values()} | set(self._asset_turns()))

    def _asset_turns(self) -> list[int]:
        return [t for p in self.assets.values() for t in p.turns]

    def mitigation_strength(self) -> float:
        """0.0 a 1.0: quanto a conversa declarou posse/autorização/defesa."""
        if not self.mitigator_turns:
            return 0.0
        return min(1.0, self.decayed_count(self.mitigator_turns) / 2.0)
