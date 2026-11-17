# Morpho

構造色シミュレーター。RCWA ソルバー S4 で多層膜・回折格子・球配列の反射スペクトルを計算し、色に変換する。
起動手順は README.md を参照。

## 構成

- `backend/` — FastAPI + S4（Python 3.14, uv）。クリーンアーキテクチャの 4 層:
  - `domain/` — エンティティ・ポート（抽象）・純粋なサービス。他の層を import しない
  - `application/usecases/` — ユースケース。domain のポート経由で外部を使う
  - `infrastructure/` — ポートの実装（S4 ソルバー、colour-science、Postgres、Firestore）
  - `presentation/` — API ルーター・DTO・依存の組み立て（`dependencies.py`）
  - 依存方向は `lint-imports`（import-linter）で強制している。application と infrastructure は互いに import しない
- `frontend/` — Next.js（App Router）+ Plotly。`app/` は画面、`components/` は UI、`lib/` は計算・API クライアント
- `openapi.json` — API 契約。frontend の `lib/api/schema.d.ts` はここから生成する
- `supabase/migrations/` — DB マイグレーション

## チェック

| いつ | 何を |
|---|---|
| ファイルを編集するたび | `.claude/hooks/lint-edited-file.sh` が ruff / eslint を自動で実行する。指摘が出たらその場で直す |
| 作業のまとまりごと | 型チェック（`cd backend && uv run pyright` / `cd frontend && npx tsc --noEmit`）と、関係するテスト |
| PR | CI（`.github/workflows/ci.yml`）が lint・型・`lint-imports`・pytest・build・API 契約を全部見る |

- backend の `uv run` は既定で S4（C++ 拡張）を含めて再同期する。S4 が要らない作業は `uv run --no-group solver …`
- S4 を使うテスト（`tests/infrastructure/test_s4_*.py`）は CI ではスキップされる。ソルバーを触ったら手元で必ず回す
- `test_s4_invariants.py` はエネルギー保存など物理的に必ず成り立つ性質のテスト。これが落ちたら実装を疑う

## API を変えたとき

```bash
cd backend && uv run --no-group solver python scripts/export_openapi.py
cd frontend && npm run gen:api
```

生成物（`openapi.json`, `frontend/lib/api/schema.d.ts`）もコミットする。忘れると CI の api-contract が落ちる。

## ハマりどころ

- frontend の lockfile は npm 11.17.0 で更新する（古い npm だと `@emnapi` が消えて `npm ci` が落ちる）
- dev サーバー（:3000 / :8000）は起動済みのことが多い。`./dev.sh` の前にポートを確認する
- 波長範囲は 380–780 nm（`frontend/lib/stack.ts` の `DEFAULT_SETTINGS`）
- デプロイは Cloud Run（S4 がネイティブ拡張のためコンテナ必須）

## 規約

- コミットは Conventional Commits、本文は日本語: `feat(frontend): …` / `fix(backend): …`
- コメントは複雑な箇所・理由が自明でない箇所だけ。何をしているかは書かない
- 1 PR = 1 テーマ。main から切る
