"use client";

import { Check, ChartLine, Pencil, Trash2, X } from "lucide-react";
import dynamic from "next/dynamic";
import { useState } from "react";

import { FileDropZone } from "@/components/FileDropZone";
import { useMaterials } from "@/components/MaterialsProvider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getMaterial, type MaterialDetail, type MaterialSummary } from "@/lib/api/client";
import { cn } from "@/lib/utils";

// Plotly はブラウザ専用なので SSR を無効化して読み込む。
const MaterialChart = dynamic(() => import("@/components/MaterialChart"), { ssr: false });

const message = (e: unknown) => (e instanceof Error ? e.message : String(e));

/** 登録した材料（波長ごとの n, k）の登録・一覧・グラフ・名前変更・削除。 */
export function MaterialLibrary() {
  const { materials, loading, loadError, reload, add, rename, remove } = useMaterials();
  // グラフを開いている材料（id → n, k の表）。複数を開いて見比べられる。
  // 登録直後もその材料のグラフを開き、読み込みが正しいかをその場で確かめられるようにする。
  const [opened, setOpened] = useState<Record<string, MaterialDetail>>({});
  const open = (detail: MaterialDetail) => setOpened((prev) => ({ ...prev, [detail.id]: detail }));
  const close = (id: string) =>
    setOpened((prev) => Object.fromEntries(Object.entries(prev).filter(([key]) => key !== id)));

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">材料を登録</CardTitle>
        </CardHeader>
        <CardContent>
          <RegisterForm
            onRegister={async (name, content) => open(await add(name, content))}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">登録した材料</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2">
          {loading && <p className="text-xs text-muted-foreground">読み込み中…</p>}
          {loadError && (
            <div className="flex items-center gap-2">
              <p className="flex-1 text-sm text-destructive">{loadError}</p>
              <Button type="button" variant="outline" size="sm" onClick={reload}>
                読み直す
              </Button>
            </div>
          )}
          {!loading && !loadError && materials.length === 0 && (
            <p className="text-xs text-muted-foreground">登録した材料はまだありません。</p>
          )}
          {materials.map((m) => (
            <MaterialRow
              key={m.id}
              material={m}
              opened={opened[m.id] ?? null}
              onOpen={async () => open(await getMaterial(m.id))}
              onClose={() => close(m.id)}
              onRename={(name) => rename(m.id, name)}
              onDelete={async () => {
                await remove(m.id);
                close(m.id);
              }}
            />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function RegisterForm({
  onRegister,
}: {
  onRegister: (name: string, content: string) => Promise<void>;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const pick = (picked: File | null) => {
    setFile(picked);
    setError(null);
    // 名前の初期値はファイル名（拡張子なし）。
    if (picked) setName(picked.name.replace(/\.[^.]+$/, ""));
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setPending(true);
    setError(null);
    try {
      await onRegister(name, await file.text());
      setFile(null);
      setName("");
    } catch (err) {
      setError(message(err));
    } finally {
      setPending(false);
    }
  };

  return (
    <form onSubmit={submit} className="grid gap-2">
      <FileDropZone
        file={file}
        onChange={pick}
        accept=".txt,.csv,.dat,.tsv,.nk,text/plain,text/csv"
        label="光学定数ファイル"
        hint="波長 nm・n・k の 3 列"
      />
      {file && (
        <div className="grid grid-cols-[1fr_auto] items-end gap-2">
          <div className="grid gap-1">
            <Label htmlFor="material-name" className="text-xs text-muted-foreground">
              材料名
            </Label>
            <Input
              id="material-name"
              required
              maxLength={100}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={pending}>
            {pending ? "登録中…" : "登録"}
          </Button>
        </div>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </form>
  );
}

function MaterialRow({
  material,
  opened,
  onOpen,
  onClose,
  onRename,
  onDelete,
}: {
  material: MaterialSummary;
  opened: MaterialDetail | null;
  onOpen: () => Promise<void>;
  onClose: () => void;
  onRename: (name: string) => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (action: () => Promise<void>) => {
    setError(null);
    try {
      await action();
    } catch (e) {
      setError(message(e));
    }
  };

  const range = opened
    ? `${opened.points[0].wavelengthNm}–${opened.points[opened.points.length - 1].wavelengthNm} nm、${opened.points.length} 点`
    : null;

  return (
    <div className="rounded-lg border p-2">
      <div className="flex items-center gap-2">
        {editing === null ? (
          <button
            type="button"
            className="flex min-w-0 flex-1 items-center gap-2 text-left text-sm font-medium hover:underline"
            onClick={() => run(opened ? async () => onClose() : onOpen)}
            title={opened ? "グラフを閉じる" : "n, k のグラフを見る"}
            aria-expanded={Boolean(opened)}
          >
            <ChartLine
              className={cn("h-4 w-4 shrink-0", opened ? "text-primary" : "text-muted-foreground")}
            />
            <span className="truncate">{material.name}</span>
          </button>
        ) : (
          <form
            className="flex flex-1 items-center gap-1"
            onSubmit={(e) => {
              e.preventDefault();
              run(async () => {
                await onRename(editing);
                setEditing(null);
              });
            }}
          >
            <Input
              autoFocus
              required
              maxLength={100}
              className="h-7"
              value={editing}
              onChange={(e) => setEditing(e.target.value)}
            />
            <Button type="submit" variant="ghost" size="icon" className="h-7 w-7" aria-label="保存">
              <Check className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              aria-label="やめる"
              onClick={() => setEditing(null)}
            >
              <X className="h-4 w-4" />
            </Button>
          </form>
        )}

        {editing === null && !confirmingDelete && (
          <>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground"
              aria-label={`${material.name} の名前を変更`}
              onClick={() => setEditing(material.name)}
            >
              <Pencil className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-destructive"
              aria-label={`${material.name} を削除`}
              onClick={() => setConfirmingDelete(true)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </>
        )}
        {confirmingDelete && (
          <div className="flex items-center gap-1 text-xs">
            <span className="text-muted-foreground">削除しますか？</span>
            <Button
              type="button"
              variant="destructive"
              size="xs"
              onClick={() => run(onDelete).finally(() => setConfirmingDelete(false))}
            >
              削除
            </Button>
            <Button type="button" variant="outline" size="xs" onClick={() => setConfirmingDelete(false)}>
              やめる
            </Button>
          </div>
        )}
      </div>

      {error && <p className="mt-1 text-sm text-destructive">{error}</p>}
      {opened && (
        <div className="mt-2 grid gap-1">
          <p className="text-xs text-muted-foreground">{range}</p>
          <MaterialChart points={opened.points} />
        </div>
      )}
    </div>
  );
}
