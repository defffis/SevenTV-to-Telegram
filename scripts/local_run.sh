#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

mkdir -p artifacts

export PYTHONPATH="${PYTHONPATH:-}:$ROOT_DIR/src"

python -m app.main sync \
  --report-path artifacts/report.json \
  --desired-state-path artifacts/desired-state.json \
  "$@" | tee artifacts/run.log
