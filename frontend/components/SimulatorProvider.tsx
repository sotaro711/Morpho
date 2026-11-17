"use client";

import { createContext, useContext, useState } from "react";

import type { EditableLayer } from "@/lib/api/client";
import { DEFAULT_DIFFRACTION_MODE, type DiffractionMode } from "@/lib/diffraction";
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
  const [mode, setMode] = useState<DiffractionMode>(DEFAULT_DIFFRACTION_MODE);
  const colorsSweep = useSweep();
  const anglesSweep = useSweep();

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
