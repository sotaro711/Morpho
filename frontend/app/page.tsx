"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

import { LayerEditor } from "@/components/LayerEditor";
import { NumberInput } from "@/components/NumberInput";
import { SettingsForm } from "@/components/SettingsForm";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import type { EditableLayer } from "@/lib/api/client";
import { useSimulation } from "@/lib/hooks/use-simulation";
import {
  DEFAULT_FILMS,
  DEFAULT_SETTINGS,
  DEFAULT_SUBSTRATE,
  structureLayers,
  toSimulationRequest,
  type Medium,
  type Settings,
} from "@/lib/stack";

// Plotly はブラウザ専用なので SSR を無効化して読み込む。
const SpectrumChart = dynamic(() => import("@/components/SpectrumChart"), {
  ssr: false,
});
const StructureView = dynamic(() => import("@/components/StructureView"), {
  ssr: false,
});

export default function Home() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [substrate, setSubstrate] = useState<Medium>(DEFAULT_SUBSTRATE);
  const [films, setFilms] = useState<EditableLayer[]>(DEFAULT_FILMS);
  const { result, error, loading, run } = useSimulation();

  const patchSettings = (p: Partial<Settings>) =>
    setSettings((s) => ({ ...s, ...p }));

  const runSimulation = () =>
    run(toSimulationRequest(settings, films, substrate));

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <header className="flex items-center gap-3">
        <div className="h-8 w-1.5 rounded-full bg-primary" />
        <h1 className="text-2xl font-bold tracking-tight">🦋 Morpho</h1>
      </header>

      <div className="mt-8 grid items-start gap-6 lg:grid-cols-[minmax(420px,460px)_1fr]">
        {/* 左：入力 */}
        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">計算条件</CardTitle>
            </CardHeader>
            <CardContent>
              <SettingsForm value={settings} onChange={patchSettings} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">多層膜</CardTitle>
              <p className="text-xs text-muted-foreground">
                上が入射側（空気）、下が基板。多層膜を上に積み上げます。
              </p>
            </CardHeader>
            <CardContent className="grid gap-3">
              <LayerEditor layers={films} onChange={setFilms} />
              <div className="border-t pt-3">
                <MediumRow label="基板" value={substrate} onChange={setSubstrate} />
              </div>
            </CardContent>
          </Card>

          <Button onClick={runSimulation} disabled={loading} className="w-full">
            {loading ? "計算中…" : "計算する"}
          </Button>
          {error && (
            <div
              role="alert"
              className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive"
            >
              エラー: {error}
            </div>
          )}
        </div>

        {/* 右：構造の断面図（常時）とスペクトル（計算後）。スクロール追従させる。 */}
        <div className="grid gap-6 lg:sticky lg:top-6 lg:self-start">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">構造の断面図</CardTitle>
            </CardHeader>
            <CardContent>
              <StructureView layers={structureLayers(films, substrate)} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">スペクトル</CardTitle>
            </CardHeader>
            <CardContent>
              {result ? (
                <>
                  <ColorSwatch color={result.reflectedColor} />
                  <SpectrumChart result={result} />
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  「計算する」を押すと結果が表示されます。
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}

function ColorSwatch({
  color,
}: {
  color: { r: number; g: number; b: number; hex: string };
}) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <div
        className="h-12 w-12 rounded-md border"
        style={{ backgroundColor: color.hex }}
      />
      <div className="text-sm">
        <div className="font-semibold">反射色（構造色）</div>
        <div className="text-muted-foreground">
          {color.hex} · RGB({color.r}, {color.g}, {color.b})
        </div>
      </div>
    </div>
  );
}

function MediumRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: Medium;
  onChange: (v: Medium) => void;
}) {
  return (
    <div className="grid grid-cols-[1fr_1fr_1fr] items-end gap-2">
      <span className="pb-2 text-sm font-semibold">{label}</span>
      <div className="grid gap-1">
        <Label className="text-xs text-muted-foreground">屈折率 n</Label>
        <NumberInput
          step={0.01}
          value={value.n}
          onChange={(n) => onChange({ ...value, n })}
        />
      </div>
      <div className="grid gap-1">
        <Label className="text-xs text-muted-foreground">消衰係数 k</Label>
        <NumberInput
          step={0.01}
          value={value.k}
          onChange={(k) => onChange({ ...value, k })}
        />
      </div>
    </div>
  );
}
