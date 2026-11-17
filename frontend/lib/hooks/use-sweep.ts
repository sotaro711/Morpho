"use client";

import { useState } from "react";

import {
  simulateSweep,
  type SweepRequest,
  type SweepResponse,
} from "@/lib/api/client";

export function useSweep() {
  const [result, setResult] = useState<SweepResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async (body: SweepRequest): Promise<SweepResponse | null> => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await simulateSweep(body);
      setResult(response);
      return response;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setResult(null);
      return null;
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
