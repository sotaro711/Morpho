"use client";

import { createContext, useContext, useState } from "react";

import type { EditableLayer } from "@/lib/api/client";
import type { DiffractionMode } from "@/lib/diffraction";
import { useSweep } from "@/lib/hooks/use-sweep";
import {
  DEFAULT_PILLAR,
  DEFAULT_SPHERE,
  type PillarConfig,
  type SphereConfig,
  type Template3D,
} from "@/lib/lattice3d";
import {
  DEFAULT_FILMS,
  DEFAULT_SETTINGS,
  DEFAULT_SUBSTRATE,
  type Medium,
  type Settings,
} from "@/lib/stack";

function useSimulator3DState() {
  const [template, setTemplate] = useState<Template3D>("sphere");
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [sphere, setSphere] = useState<SphereConfig>(DEFAULT_SPHERE);
  const [sphereSubstrate, setSphereSubstrate] =
    useState<Medium>(DEFAULT_SUBSTRATE);
  const [pillar, setPillar] = useState<PillarConfig>(DEFAULT_PILLAR);
  const [pillarFilms, setPillarFilms] =
    useState<EditableLayer[]>(DEFAULT_FILMS);
  const [pillarSubstrate, setPillarSubstrate] =
    useState<Medium>(DEFAULT_SUBSTRATE);
  const [mode, setMode] = useState<DiffractionMode>("zeroth");
  const colorsSweep = useSweep(); // 色チップ + 角度別スペクトル
  const anglesSweep = useSweep(); // 角度スイープチャート

  return {
    template,
    setTemplate,
    settings,
    setSettings,
    sphere,
    setSphere,
    sphereSubstrate,
    setSphereSubstrate,
    pillar,
    setPillar,
    pillarFilms,
    setPillarFilms,
    pillarSubstrate,
    setPillarSubstrate,
    mode,
    setMode,
    colorsSweep,
    anglesSweep,
  };
}

const Simulator3DContext = createContext<ReturnType<
  typeof useSimulator3DState
> | null>(null);

/** 3 次元構造の計算画面の入力と結果。SimulatorProvider と同じく、ページを離れても残す。 */
export function Simulator3DProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Simulator3DContext.Provider value={useSimulator3DState()}>
      {children}
    </Simulator3DContext.Provider>
  );
}

export function useSimulator3D() {
  const value = useContext(Simulator3DContext);
  if (!value)
    throw new Error("useSimulator3D は Simulator3DProvider の内側で使う");
  return value;
}
