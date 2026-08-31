# Arquitetura do ContextGuard

Documento de apoio ao **SeloS** (artefato sustentável): descreve os arquivos, as
funções principais e o fluxo de dados, para que um revisor consiga mapear cada
reivindicação do relatório ao código.

## Ideia em uma frase

Um filtro sem estado avalia `f(turno_i)`. Um ataque que decompõe um objetivo `G`
em fragmentos `g1..gn` com `f(gi) = benigno` para todo `i` derrota esse filtro
**por construção** — é uma falha de escopo, não de calibração. O ContextGuard
troca o escopo: avalia `f(turno_1..turno_i)`, tratando a conversa como um
**acumulador de capacidade**.

## Fluxo de um turno

```
                 texto do turno (a defesa NÃO vê o objetivo)
                        │
          features.extract()         ← taxonomy.json (léxicos)
                        │  TurnFeatures(targets, phases, specificity, frames, anaphora, mitigators)
                        ▼
          ConversationState.update()  ← acumula por conversa, com decaimento
                        │
        ┌───────────────┼───────────────┬───────────────┬──────────────┐
        ▼               ▼               ▼               ▼              ▼
  Composition     Escalation    TargetPersistence   FrameShift     Chaining     (detectors/)
        └───────────────┴───────────────┴───────────────┴──────────────┘
                        │  lista de Evidence
                        ▼
                 policy.assess()   → soma ponderada − mitigação; regra dura
                 policy.decide()   → ALLOW / FLAG / BLOCK  (Verdict + evidências)
                        │
                        ▼
                 arena.run()  →  alvo entrega o fragmento se não houve BLOCK
                        │
                        ▼
                 criterion.evaluate()  →  sucesso? bloqueio tardio?
```

## Mapa de arquivos

| Arquivo | Papel |
|---|---|
| `model.py` | Tipos: `Turn` (o que a defesa vê), `AnnotatedTurn` (o que o cenário declara), `Evidence`, `Verdict`, `Scenario`, `RunResult`. |
| `features.py` | `extract()` — texto → sinais nomeados, a partir de `taxonomy.json`. Função pura. |
| `taxonomy.json` | Léxicos (alvos, fases, especificidade, molduras, anáfora, mitigadores). Principal ponto de ajuste — e principal fraqueza. |
| `state.py` | `ConversationState` — acumulador da conversa, com decaimento exponencial (`half_life`). |
| `detectors/` | Cinco detectores (padrão Strategy). Cada um responde uma pergunta e devolve `Evidence`. |
| `policy.py` | `assess()` + `decide()` — agrega evidências, aplica mitigação e a regra dura, decide o veredito. |
| `defenses/per_turn.py` | **Baseline** sem estado (blocklist + composição intra-turno). |
| `defenses/contextguard.py` | **Defesa com estado**; modo `memoryless` para a Reivindicação #1. |
| `target.py` | `SimulatedTarget` — entrega o fragmento se o turno não foi bloqueado. Determinístico. |
| `arena.py` | Laço turno a turno. Garante o **isolamento** (`as_turn()`) e a continuidade após bloqueio. |
| `criterion.py` | Define e afere o **sucesso do ataque** (checklist de fragmentos) + métricas. |
| `attack/plan.py` | `AttackPlan` — valida que os turnos cobrem o objetivo declarado. |
| `attack/transforms.py` | Transformações evasivas: `dilute`, `paraphrase`, `claim_authority`. |
| `loader.py` | Carrega e **valida** os cenários JSON (falha cedo se um cenário for incoerente). |
| `report.py` | Gera as cinco tabelas (CSV + Markdown). |
| `__main__.py` | CLI: `list`, `demo`, `run`, `experiment`, `ablation`. |

## Os cinco detectores

| Detector | Pergunta | Peso |
|---|---|---|
| `composition` | Quantas etapas distintas da cadeia a conversa cobriu sobre conteúdo sensível? | 0.40 |
| `escalation` | O pedido saiu do conceitual e chegou ao operacional? | 0.20 |
| `target_persistence` | Algum ativo sensível é o eixo da conversa? | 0.15 |
| `frame_shift` | O pretexto mudou enquanto o assunto sensível permaneceu? | 0.15 |
| `chaining` | Este turno só faz sentido por causa dos anteriores (anáfora)? | 0.10 |

Os pesos somam 1.0 (verificado em `tests/test_detectors.py`), então o score
bruto vive em `[0, 1]` e os limiares de `policy.py` são frações do sinal máximo.

## Decisões de projeto (as que um revisor deve questionar)

1. **Acumulador por conversa, não por alvo.** Uma operação real toca vários
   ativos (phishing = canal de e-mail + credenciais). Amarrar a composição a um
   único ativo perderia o sinal que o desafio pede para enxergar.
2. **Decaimento exponencial.** Sem ele, qualquer conversa longa sobre assunto
   sensível acabaria bloqueada; com ele, a defesa esquece o passado distante — e
   é exatamente essa porta que o ataque por **diluição** explora (R5).
3. **Regra dura derivada das evidências.** O bloqueio forte depende de os
   detectores de composição/escalada terem apontado o sinal — para que a ablação
   (R4) desarme de fato o caminho de bloqueio ao desligá-los.
4. **Mitigação é desconto, não imunidade.** Posse/autorização declaradas reduzem
   o score, mas são auto-declaradas e falsificáveis — o que o ataque por
   **autoridade** explora (R5).
