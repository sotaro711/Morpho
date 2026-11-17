#!/bin/bash
# Edit / Write の直後に、そのファイルだけフォーマットと lint をかける（PostToolUse hook）。
# 直せない指摘が残ったら exit 2 で stderr を Claude に返し、その場で直させる。
# 型チェック・テスト・build は重いので CI に任せる。
set -u

file=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input", {}).get("file_path", ""))')
root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"

case "$file" in
  "$root"/backend/vendor/* | "$root"/backend/.venv/* | "$root"/frontend/node_modules/*) ;;
  "$root"/backend/*.py)
    cd "$root/backend" || exit 0
    # --no-sync: 既定の再同期で S4（C++ 拡張）のビルドが走るのを避ける。
    uv run --no-sync ruff format -q "$file"
    out=$(uv run --no-sync ruff check --fix -q "$file" 2>&1) || { echo "$out" >&2; exit 2; }
    ;;
  "$root"/frontend/*.ts | "$root"/frontend/*.tsx)
    cd "$root/frontend" || exit 0
    out=$(npx --no-install eslint --fix --max-warnings 0 "$file" 2>&1) || { echo "$out" >&2; exit 2; }
    ;;
esac
exit 0
