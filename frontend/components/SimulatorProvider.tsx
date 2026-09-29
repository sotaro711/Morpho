"use client";

import { createContext, useContext, useState } from "react";

import type { EditableLayer } from "@/lib/api/client";
import type { DiffractionMode } from "@/lib/diffraction";
import { useSweep } from "@/lib/hooks/use-sweep";
import {
  DEFAULT_FILMS,
  DEFAULT_SETTINGS,
  DEFAULT_SUBSTRATE,
  type Medium,
  type Settings,
} from "@/lib/stack";
import { DEFAULT_STEPPED, type SteppedConfig } from "@/lib/stepped";

function useSimulatorState() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [substrate, setSubstrate] = useState<Medium>(DEFAULT_SUBSTRATE);
  const [films, setFilms] = useState<EditableLayer[]>(DEFAULT_FILMS);
  const [stepped, setStepped] = useState<SteppedConfig>(DEFAULT_STEPPED);
  // 表示する回折次数の見方（0次のみ / 0次以外 / 全次数）。表示だけの切替で再計算はしない。
  const [mode, setMode] = useState<DiffractionMode>("zeroth");
  const colorsSweep = useSweep(); // 色チップ + 角度別スペクトル
  const anglesSweep = useSweep(); // 角度スイープチャート

  return {
    settings,
    setSettings,
    substrate,
    setSubstrate,
    films,
    setFilms,
    stepped,
    setStepped,
    mode,
    setMode,
    colorsSweep,
    anglesSweep,
  };
}

const SimulatorContext = createContext<ReturnType<typeof useSimulatorState> | null>(null);

/**
 * 計算画面の入力と結果。ページより外（レイアウト）に置き、材料ページへ移って戻っても
 * 編集中の層や計算結果が消えないようにする。リロードすると初期値に戻る。
 */
export function SimulatorProvider({ children }: { children: React.ReactNode }) {
  return (
    <SimulatorContext.Provider value={useSimulatorState()}>{children}</SimulatorContext.Provider>
  );
}

export function useSimulator() {
  const value = useContext(SimulatorContext);
  if (!value) throw new Error("useSimulator は SimulatorProvider の内側で使う");
  return value;
}
