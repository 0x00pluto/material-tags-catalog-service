#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
    echo "已从 .env.example 复制出 .env，请先编辑 CATALOG_ROOT 后再启动。"
    ${EDITOR:-open} .env || true
    exit 1
  fi
  echo "缺少 .env，请复制 .env.example 为 .env 并设置 CATALOG_ROOT。"
  exit 1
fi

cp -f .env ./catalog-service/.env
chmod +x ./catalog-service/catalog-service 2>/dev/null || true
echo "启动 catalog-service ..."
./catalog-service/catalog-service
