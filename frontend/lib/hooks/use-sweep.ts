"use client";

import { useState } from "react";

import {
  simulateSweep,
  type SweepRequest,
  type SweepResponse,
} from "@/lib/api/client";

/**
 * 入射角スイープの実行と、その実行状態を管理する。
 *
 * use-simulation.ts と同じ形(「API を呼び、その状態を持つ」だけ)。
 * 結果表示は 2 種類のスイープ(色+スペクトル用 / 角度チャート用)を使うため、
 * 呼び出し側でこのフックを 2 インスタンス並べて使う。
 * clear() は段差なしに戻したとき等に古い結果を消すためにある。
 */
export function useSweep() {
  const [result, setResult] = useState<SweepResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async (body: SweepRequest) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await simulateSweep(body));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const clear = () => {
    setResult(null);
    setError(null);
  };

  return { result, error, loading, run, clear };
}
