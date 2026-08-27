"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

import { LayerEditor } from "@/components/LayerEditor";
import { NumberInput } from "@/components/NumberInput";
import { SettingsForm } from "@/components/SettingsForm";
import { StepEditor } from "@/components/StepEditor";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import type { EditableLayer, SweepResponse } from "@/lib/api/client";
import { useSweep } from "@/lib/hooks/use-sweep";
import {
  DEFAULT_FILMS,
  DEFAULT_SETTINGS,
  DEFAULT_SUBSTRATE,
  structureLayers,
  type Medium,
  type Settings,
} from "@/lib/stack";
import {
  DEFAULT_STEPPED,
  toSteppedSimulationRequest,
  type SteppedConfig,
} from "@/lib/stepped";

// Plotly はブラウザ専用なので SSR を無効化して読み込む。
const StructureView = dynamic(() => import("@/components/StructureView"), {
  ssr: false,
});
const AngleSweepChart = dynamic(() => import("@/components/AngleSweepChart"), {
  ssr: false,
});
const AngleSpectraChart = dynamic(
  () => import("@/components/AngleSpectraChart"),
  { ssr: false },
);

// 見た目の色・角度別スペクトル用: 0/30/60°、波長は 10nm 間隔(色変換できる間隔)。
const COLOR_THETAS = [0, 30, 60];
const COLOR_SWEEP_WL = { wlMin: 380, wlMax: 780, wlPoints: 41 };
// 角度スイープチャート用: -80〜80° を 10° 刻み、代表 5 波長(400/475/550/625/700)。
const ANGLE_THETAS = Array.from({ length: 17 }, (_, i) => -80 + i * 10);
const ANGLE_SWEEP_WL = { wlMin: 400, wlMax: 700, wlPoints: 5 };

export default function Home() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [substrate, setSubstrate] = useState<Medium>(DEFAULT_SUBSTRATE);
  const [films, setFilms] = useState<EditableLayer[]>(DEFAULT_FILMS);
  const [stepped, setStepped] = useState<SteppedConfig>(DEFAULT_STEPPED);
  const colorsSweep = useSweep(); // 色チップ + 角度別スペクトル
  const anglesSweep = useSweep(); // 角度スイープチャート
  const loading = colorsSweep.loading || anglesSweep.loading;
  const error = colorsSweep.error ?? anglesSweep.error;

  const patchSettings = (p: Partial<Settings>) =>
    setSettings((s) => ({ ...s, ...p }));

  const runSimulation = async () => {
    // 段差の有無は選ぶものではなく、設定の結果として決まる。
    const base = toSteppedSimulationRequest(settings, films, substrate, stepped);
    // 直列に実行する: バックエンドは 1 リクエストずつ解くので並列でも速くならず、
    // 待ち行列に入った方がプロキシタイムアウトに達するリスクだけが増えるため。
    await colorsSweep.run({
      ...base,
      ...COLOR_SWEEP_WL,
      thetaDegs: COLOR_THETAS,
      includeColors: true,
    });
    await anglesSweep.run({
      ...base,
      ...ANGLE_SWEEP_WL,
      thetaDegs: ANGLE_THETAS,
      includeColors: false,
    });
  };

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
            </CardHeader>
            <CardContent className="grid gap-3">
              <LayerEditor layers={films} onChange={setFilms} />
              <div className="border-t pt-3">
                <MediumRow label="基板" value={substrate} onChange={setSubstrate} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">段差</CardTitle>
            </CardHeader>
            <CardContent>
              <StepEditor value={stepped} onChange={setStepped} />
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
              <CardTitle className="text-base">見た目の色</CardTitle>
            </CardHeader>
            <CardContent>
              {colorsSweep.result ? (
                <AngleColorChips sweep={colorsSweep.result} />
              ) : (
                <p className="text-sm text-muted-foreground">
                  {colorsSweep.loading
                    ? "計算中…（段付き構造では数分かかります）"
                    : "「計算する」を押すと結果が表示されます。"}
                </p>
              )}
            </CardContent>
          </Card>

          {(anglesSweep.result || anglesSweep.loading) && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">角度スイープ</CardTitle>
              </CardHeader>
              <CardContent>
                {anglesSweep.result ? (
                  <AngleSweepChart sweep={anglesSweep.result} />
                ) : (
                  <p className="text-sm text-muted-foreground">計算中…</p>
                )}
              </CardContent>
            </Card>
          )}

          {colorsSweep.result && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">反射スペクトル（角度ごとの波長依存性）</CardTitle>
              </CardHeader>
              <CardContent>
                <AngleSpectraChart sweep={colorsSweep.result} />
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </main>
  );
}

/** 入射角ごとの見た目の色チップ(研究スライド上段の形式)。 */
function AngleColorChips({ sweep }: { sweep: SweepResponse }) {
  return (
    <div className="flex justify-center gap-8">
      {sweep.entries.map((e) => (
        <div key={e.thetaDeg} className="grid justify-items-center gap-1.5">
          <span className="text-sm font-semibold">{Math.round(e.thetaDeg)}°</span>
          <div
            className="h-16 w-16 rounded-md border"
            style={{ backgroundColor: e.color?.hex }}
          />
          <span className="text-xs text-muted-foreground">{e.color?.hex}</span>
        </div>
      ))}
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
