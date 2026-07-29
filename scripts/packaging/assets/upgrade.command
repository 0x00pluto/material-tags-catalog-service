#!/bin/bash
# From the portable deploy root: fetch latest GitHub Release zip for this OS/arch,
# stop catalog-service, merge-extract (never overwrite existing .env).
set -euo pipefail

DEPLOY_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$DEPLOY_ROOT"

DEFAULT_REPO="0x00pluto/material-tags-catalog-service"
REPO="${CATALOG_UPDATE_REPO:-$DEFAULT_REPO}"
TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"

YES=0
for arg in "$@"; do
  case "$arg" in
    -y|--yes) YES=1 ;;
    -h|--help)
      echo "Usage: $(basename "$0") [-y|--yes]"
      echo "  Fetches latest Release zip for this Mac arch from GitHub and merge-upgrades in place."
      echo "  Env: CATALOG_UPDATE_REPO=owner/repo  GITHUB_TOKEN / GH_TOKEN (optional)"
      exit 0
      ;;
  esac
done

detect_arch() {
  local m
  m="$(uname -m | tr '[:upper:]' '[:lower:]')"
  case "$m" in
    x86_64|amd64) echo amd64 ;;
    arm64|aarch64) echo arm64 ;;
    *)
      echo "Unsupported arch: $m" >&2
      exit 1
      ;;
  esac
}

OS_NAME="macos"
ARCH="$(detect_arch)"

echo "Deploy root: $DEPLOY_ROOT"
echo "Platform: ${OS_NAME}-${ARCH}"
echo "Repo: $REPO"

local_version() {
  local bin="$DEPLOY_ROOT/catalog-service/catalog-service"
  if [[ ! -f "$bin" ]]; then
    echo ""
    return
  fi
  local out
  out="$("$bin" --version 2>/dev/null || true)"
  echo "$out" | python3 -c 'import re,sys; m=re.search(r"(\d+\.\d+\.\d+(?:\+[^\s]+)?)", sys.stdin.read()); print(m.group(1) if m else "")' 2>/dev/null || true
}

CURL_HEADERS=(-H "Accept: application/vnd.github+json" -H "User-Agent: material-tags-catalog-upgrade")
if [[ -n "$TOKEN" ]]; then
  CURL_HEADERS+=(-H "Authorization: Bearer $TOKEN")
fi

API_URL="https://api.github.com/repos/${REPO}/releases/latest"
echo "Fetching $API_URL ..."
TMP_JSON="$(mktemp)"
if ! curl -fsSL "${CURL_HEADERS[@]}" "$API_URL" -o "$TMP_JSON"; then
  rm -f "$TMP_JSON"
  echo "Failed to fetch latest release." >&2
  exit 1
fi

PARSE_OUT="$(python3 - "$TMP_JSON" "$OS_NAME" "$ARCH" <<'PY'
import json, sys
path, os_name, arch = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, encoding="utf-8") as f:
    release = json.load(f)
suffix = f"-{os_name}-{arch}.zip"
prefix = "material-tags-catalog-"
for a in release.get("assets") or []:
    name = a.get("name") or ""
    if name.startswith(prefix) and name.endswith(suffix):
        mid = name[len(prefix) : -len(suffix)]
        if mid:
            print(name)
            print(a.get("browser_download_url") or "")
            print(mid)
            sys.exit(0)
sys.exit(2)
PY
)" || {
  rm -f "$TMP_JSON"
  echo "No asset matching material-tags-catalog-*-${OS_NAME}-${ARCH}.zip in latest release." >&2
  exit 1
}
rm -f "$TMP_JSON"

ASSET_NAME="$(printf '%s\n' "$PARSE_OUT" | sed -n '1p')"
ASSET_URL="$(printf '%s\n' "$PARSE_OUT" | sed -n '2p')"
REMOTE_VERSION="$(printf '%s\n' "$PARSE_OUT" | sed -n '3p')"

LOCAL_VERSION="$(local_version)"
echo "Remote: $ASSET_NAME (version=$REMOTE_VERSION)"
echo "Local version: ${LOCAL_VERSION:-'(unknown)'}"

if [[ -n "$LOCAL_VERSION" && "$LOCAL_VERSION" == "$REMOTE_VERSION" ]]; then
  echo "Already up to date ($LOCAL_VERSION). Nothing to do."
  exit 0
fi

if [[ "$YES" -ne 1 ]]; then
  read -r -p "Download and merge-upgrade to ${ASSET_NAME}? [y/N] " ans || true
  case "$ans" in
    y|Y) ;;
    *)
      echo "Cancelled."
      exit 0
      ;;
  esac
fi

TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/mtc-upgrade.XXXXXX")"
cleanup() { rm -rf "$TEMP_ROOT"; }
trap cleanup EXIT

ZIP_PATH="$TEMP_ROOT/$ASSET_NAME"
EXTRACT_DIR="$TEMP_ROOT/extract"
mkdir -p "$EXTRACT_DIR"

echo "Stopping catalog-service (if running) ..."
pkill -f "/catalog-service/catalog-service" 2>/dev/null || true
pkill -x catalog-service 2>/dev/null || true
sleep 1

if [[ -f "$DEPLOY_ROOT/.env" ]]; then
  cp -f "$DEPLOY_ROOT/.env" "$DEPLOY_ROOT/.env.bak.upgrade"
  echo "Backed up .env -> .env.bak.upgrade"
fi

echo "Downloading $ASSET_URL ..."
curl -fsSL "${CURL_HEADERS[@]}" -L -o "$ZIP_PATH" "$ASSET_URL"

echo "Extracting ..."
unzip -q "$ZIP_PATH" -d "$EXTRACT_DIR"

TOP_DIRS=()
while IFS= read -r line; do
  TOP_DIRS+=("$line")
done < <(find "$EXTRACT_DIR" -mindepth 1 -maxdepth 1 -type d)

if [[ ${#TOP_DIRS[@]} -ne 1 ]]; then
  echo "Expected exactly one top-level directory in zip, found ${#TOP_DIRS[@]}." >&2
  exit 1
fi

PACKAGE_DIR="${TOP_DIRS[0]}"
echo "Merging from $PACKAGE_DIR ..."

# Merge package root entries; never overwrite existing deploy-root .env
# Enable dotglob so .env.example is copied; skip . and ..
shopt -s dotglob nullglob
for item in "$PACKAGE_DIR"/*; do
  base="$(basename "$item")"
  if [[ "$base" == "." || "$base" == ".." ]]; then
    continue
  fi
  if [[ "$base" == ".env" && -f "$DEPLOY_ROOT/.env" ]]; then
    echo "Skip existing .env"
    continue
  fi
  if [[ -d "$item" ]]; then
    mkdir -p "$DEPLOY_ROOT/$base"
    if command -v rsync >/dev/null 2>&1; then
      rsync -a "$item"/ "$DEPLOY_ROOT/$base"/
    else
      cp -R "$item"/. "$DEPLOY_ROOT/$base"/
    fi
  else
    cp -f "$item" "$DEPLOY_ROOT/$base"
  fi
done
shopt -u dotglob nullglob

chmod +x "$DEPLOY_ROOT/catalog-service/catalog-service" 2>/dev/null || true
chmod +x "$DEPLOY_ROOT/build-catalog/build-catalog" 2>/dev/null || true
chmod +x "$DEPLOY_ROOT/start.command" 2>/dev/null || true
chmod +x "$DEPLOY_ROOT/upgrade.command" 2>/dev/null || true

echo ""
echo "Upgrade files merged. .env was preserved if present."
echo "Next: double-click start.command, then open http://127.0.0.1:8787/health and check version=$REMOTE_VERSION"
exit 0
