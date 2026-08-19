"use client";

import { useState } from "react";

import {
  simulate,
  type SimulationRequest,
  type SimulationResponse,
} from "@/lib/api/client";

/**
 * シミュレーションの実行と、その実行状態（結果・エラー・実行中）を管理する。
 *
 * 責務は「API を呼び、その状態を持つ」ことだけに限定する。リクエストの組み立ては
 * lib/stack.ts の toSimulationRequest() が担当し、このフックは組み立て済みの
 * SimulationRequest を受け取る。こうしておくと、今後 角度掃引などの別エンドポイントを
 * 足すときに同じ形のフックを横に並べられる。
 */
export function useSimulation() {
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async (body: SimulationRequest) => {
    setLoading(true);
    setError(null);
    try {
      setResult(await simulate(body));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return { result, error, loading, run };
}
