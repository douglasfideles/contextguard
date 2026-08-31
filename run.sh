#!/usr/bin/env bash
# Atalho para rodar o ContextGuard direto na máquina (sem Docker).
# Uso:
#   ./run.sh demo           # trace turno a turno de um ataque nas duas defesas
#   ./run.sh experiment     # gera as 5 tabelas em results/
#   ./run.sh list           # lista os cenários
#   ./run.sh testes         # roda a suíte de testes (pytest)
#   ./run.sh run --scenario phishing_credencial --defense contextguard
set -euo pipefail

cd "$(dirname "$0")"
export PYTHONPATH="src"

if [[ "${1:-}" == "testes" ]]; then
  exec python3 -m pytest -q
fi

exec python3 -m contextguard "$@"
