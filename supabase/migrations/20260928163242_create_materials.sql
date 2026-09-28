-- ユーザーが登録した材料（波長ごとの n, k の表）。
-- 読み書きは FastAPI だけが行い、ブラウザから直接は触らない。
-- 設計判断は Notion「🧪 材料 DB（波長分散データ）」を参照。
create table public.materials (
  id             uuid        primary key default gen_random_uuid(),
  owner          uuid        not null references auth.users (id) on delete cascade,
  name           text        not null,
  -- 3 列は同じ長さで、同じ位置の要素が 1 つの測定点（波長 nm, n, k）を表す。
  wavelengths_nm float8[]    not null,
  n              float8[]    not null,
  k              float8[]    not null,
  created_at     timestamptz not null default now(),

  -- 材料名はユーザーごとに一意（大文字小文字は区別）。一覧は名前だけなので、名前で見分けられる必要がある。
  unique (owner, name),
  check (name = btrim(name) and char_length(name) between 1 and 100),
  check (cardinality(wavelengths_nm) between 2 and 5000),
  check (cardinality(n) = cardinality(wavelengths_nm)
     and cardinality(k) = cardinality(wavelengths_nm)),
  check (0 < all (wavelengths_nm) and 0 < all (n) and 0 <= all (k))
);

-- ポリシーは作らない。公開キー経由の PostgREST（anon / authenticated）からは一切読み書きできず、
-- テーブル所有者として接続する FastAPI だけが扱える。
-- 波長の昇順・重複なし・380〜780 nm を含むことはアプリ側で検証する。
alter table public.materials enable row level security;
