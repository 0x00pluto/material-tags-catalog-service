#!/usr/bin/env bash
# 一键启动本仓开发/联调 HTTP 服务（watch + 定时 + FastAPI）。
# 用法：
#   ./scripts/catalog_service/dev-serve.sh
#   ./scripts/catalog_service/dev-serve.sh /path/to/media-library
#   CATALOG_ROOT=/path/to/media ./scripts/catalog_service/dev-serve.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

PY="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "缺少 .venv。请先：uv venv && uv pip install -r requirements.txt" >&2
  exit 1
fi

# 优先级：命令行参数 > 环境变量 CATALOG_ROOT > .env > temp 样例盘
ROOT_ARG="${1:-}"
if [[ -n "$ROOT_ARG" ]]; then
  export CATALOG_ROOT="$ROOT_ARG"
elif [[ -z "${CATALOG_ROOT:-}" ]]; then
  if [[ -f "$REPO_ROOT/.env" ]] && grep -qE '^[[:space:]]*CATALOG_ROOT=' "$REPO_ROOT/.env"; then
    : # Settings 会读 .env
  else
    DEV_ROOT="$REPO_ROOT/temp/dev-media"
    mkdir -p "$DEV_ROOT"
    TAGS="$DEV_ROOT/demo.material-tags.json"
    MEDIA="$DEV_ROOT/demo.mp4"
    if [[ ! -f "$TAGS" ]]; then
      cat >"$TAGS" <<'EOF'
{
  "schema_version": "1",
  "generated_at": "2026-07-30T00:00:00+08:00",
  "title": "本地开发样例",
  "description": "dev-serve 自动生成的样例标签，可删可改",
  "keywords": "demo, 开发, 样例"
}
EOF
    fi
    if [[ ! -f "$MEDIA" ]]; then
      printf 'fake' >"$MEDIA"
    fi
    export CATALOG_ROOT="$DEV_ROOT"
    echo "未配置 CATALOG_ROOT，使用临时样例盘: $DEV_ROOT"
  fi
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8787}"

echo "启动 catalog 服务…"
echo "  root=${CATALOG_ROOT:-(.env)}"
echo "  http://$HOST:$PORT/health"
echo "  http://$HOST:$PORT/docs"
echo "Ctrl+C 停止"
echo

exec "$PY" "$REPO_ROOT/scripts/catalog_service/serve.py" \
  --host "$HOST" \
  --port "$PORT" \
  ${CATALOG_ROOT:+--root "$CATALOG_ROOT"}
