"use client";

import { ChevronRight, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { ResultDetail } from "@/components/ResultDetail";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  deleteResult,
  getResult,
  listResults,
  type ResultDetail as Detail,
  type ResultSummary,
} from "@/lib/api/client";
import { cn } from "@/lib/utils";

const message = (e: unknown) => (e instanceof Error ? e.message : String(e));

/** 計算の履歴（計算するたびに自動で保存される結果）の一覧・詳細・削除。 */
export function ResultHistory() {
  const [results, setResults] = useState<ResultSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  // 読み直すたびに増やして、下の effect で一覧を取り直す。
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    // 開発時の StrictMode で 2 回走っても、片付け済みの 1 回目の結果は捨てる。
    let active = true;
    listResults()
      .then((list) => active && setResults(list))
      .catch((e: unknown) => active && setLoadError(message(e)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [attempt]);

  const reload = () => {
    setLoading(true);
    setLoadError(null);
    setAttempt((n) => n + 1);
  };

  const remove = async (id: string) => {
    await deleteResult(id);
    setResults((prev) => prev.filter((r) => r.id !== id));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">履歴</CardTitle>
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
        {!loading && !loadError && results.length === 0 && (
          <p className="text-xs text-muted-foreground">まだ計算していません。</p>
        )}
        {results.map((r) => (
          <ResultRow key={r.id} result={r} onDelete={() => remove(r.id)} />
        ))}
      </CardContent>
    </Card>
  );
}

function ResultRow({
  result,
  onDelete,
}: {
  result: ResultSummary;
  onDelete: () => Promise<void>;
}) {
  const [opened, setOpened] = useState<Detail | null>(null);
  const [opening, setOpening] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = async () => {
    if (opened) {
      setOpened(null);
      return;
    }
    setError(null);
    setOpening(true);
    try {
      setOpened(await getResult(result.id));
    } catch (e) {
      setError(message(e));
    } finally {
      setOpening(false);
    }
  };

  const confirmDelete = async () => {
    setError(null);
    try {
      await onDelete();
    } catch (e) {
      setError(message(e));
      setConfirmingDelete(false);
    }
  };

  return (
    <div className="rounded-lg border p-2">
      <div className="flex items-center gap-3">
        <button
          type="button"
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
          onClick={toggle}
          disabled={opening}
          aria-expanded={Boolean(opened)}
        >
          <ChevronRight
            className={cn(
              "h-4 w-4 shrink-0 text-muted-foreground transition-transform",
              opened && "rotate-90",
            )}
          />
          <span className="text-sm font-medium hover:underline">
            {new Date(result.createdAt).toLocaleString("ja-JP")}
          </span>
        </button>

        <div className="flex gap-1.5">
          {result.colors.map((c) => (
            <div key={c.thetaDeg} className="grid justify-items-center gap-0.5">
              <div
                className="h-6 w-6 rounded border"
                style={{ backgroundColor: c.color.hex }}
                title={c.color.hex}
              />
              <span className="text-[10px] text-muted-foreground">
                {Math.round(c.thetaDeg)}°
              </span>
            </div>
          ))}
        </div>

        {confirmingDelete ? (
          <div className="flex items-center gap-1 text-xs">
            <span className="text-muted-foreground">削除しますか？</span>
            <Button type="button" variant="destructive" size="xs" onClick={confirmDelete}>
              削除
            </Button>
            <Button
              type="button"
              variant="outline"
              size="xs"
              onClick={() => setConfirmingDelete(false)}
            >
              やめる
            </Button>
          </div>
        ) : (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-destructive"
            aria-label="この結果を削除"
            onClick={() => setConfirmingDelete(true)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </div>
      {error && <p className="mt-1 text-sm text-destructive">{error}</p>}
      {opening && <p className="mt-2 text-xs text-muted-foreground">読み込み中…</p>}
      {opened && (
        <div className="mt-3 border-t pt-3">
          <ResultDetail result={opened} />
        </div>
      )}
    </div>
  );
}
