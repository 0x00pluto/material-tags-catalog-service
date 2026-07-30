#!/usr/bin/env bash
# 一键跑本仓 pytest。
# 用法：
#   ./scripts/catalog_service/dev-test.sh
#   ./scripts/catalog_service/dev-test.sh tests/src/catalog_service/test_builder.py -q
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

PY="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "缺少 .venv。请先：uv venv && uv pip install -r requirements.txt" >&2
  exit 1
fi

if [[ $# -eq 0 ]]; then
  exec "$PY" -m pytest -q
else
  exec "$PY" -m pytest "$@"
fi
