"use client";

import dynamic from "next/dynamic";

import { DiffractionModeToggle } from "@/components/DiffractionModeToggle";
import { LayerEditor } from "@/components/LayerEditor";
import { Field } from "@/components/Field";
import { OpticsFields } from "@/components/OpticsFields";
import { PairInsertForm } from "@/components/PairInsertForm";
import { SettingsForm } from "@/components/SettingsForm";
import { useSimulator } from "@/components/SimulatorProvider";
import { StepEditor } from "@/components/StepEditor";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { SweepResponse } from "@/lib/api/client";
import {
  entryColor,
  hasDiffractionModes,
  type DiffractionMode,
} from "@/lib/diffraction";
import { structureLayers, type Medium, type Settings } from "@/lib/stack";
import { isStepped, structureColumns, toSteppedSimulationRequest } from "@/lib/stepped";

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
// 角度スイープチャート用: -80〜80° を 10° 刻み、代表 5 波長。
// 波長は研究スライド(COMSOL 参照結果)と同じ値。550nm 付近はストップバンドの
// 急峻な端で 10nm ずれると曲線の形が変わるため、等間隔グリッドではなく明示する。
const ANGLE_THETAS = Array.from({ length: 17 }, (_, i) => -80 + i * 10);
const ANGLE_SWEEP_WL = { wavelengthsNm: [400, 470, 540, 600, 700] };

export default function Home() {
  const {
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
  } = useSimulator();
  const loading = colorsSweep.loading || anglesSweep.loading;
  const error = colorsSweep.error ?? anglesSweep.error;

  const patchSettings = (p: Partial<Settings>) =>
    setSettings((s) => ({ ...s, ...p }));

  const runSimulation = async () => {
    // 段差の有無は選ぶものではなく、設定の結果として決まる。
    const base = toSteppedSimulationRequest(settings, films, substrate, stepped);
    // 直列に実行する: バックエンドは 1 リクエストずつ解くので並列でも速くならず、
    // 待ち行列に入った方がプロキシタイムアウトに達するリスクだけが増えるため。
    // 2 本目の run が始まるまで前回の角度チャートが残らないよう、先に消しておく。
    anglesSweep.clear();
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
    <div className="mx-auto w-full max-w-6xl px-6 py-6">
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(420px,460px)_1fr]">
        {/* 左：入力 */}
        <div className="grid min-w-0 gap-6">
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
              <CardTitle className="text-base">ペアをまとめて挿入</CardTitle>
            </CardHeader>
            <CardContent>
              {/* 多層膜スタックの一番上（入射側寄り）にまとめて積む */}
              <PairInsertForm
                onInsert={(block) => setFilms((prev) => [...block, ...prev])}
              />
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

          {/* 層を増やして左カラムが長くなってもスクロールせずに押せるよう、画面下端に追従させる */}
          <div className="sticky bottom-0 z-10 grid gap-3 border-t bg-background/85 py-3 backdrop-blur">
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
        </div>

        {/* 右：構造の断面図（常時）とスペクトル（計算後）。スクロール追従させる。 */}
        <div className="grid min-w-0 gap-6 lg:sticky lg:top-6 lg:self-start">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">構造の断面図</CardTitle>
            </CardHeader>
            <CardContent>
              <StructureView
                layers={structureLayers(films, substrate)}
                stepped={
                  isStepped(stepped)
                    ? structureColumns(films, substrate, stepped)
                    : undefined
                }
              />
            </CardContent>
          </Card>

          {hasDiffractionModes(colorsSweep.result) && (
            <Card>
              <CardContent>
                <DiffractionModeToggle value={mode} onChange={setMode} />
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">見た目の色</CardTitle>
            </CardHeader>
            <CardContent>
              {colorsSweep.result ? (
                <AngleColorChips sweep={colorsSweep.result} mode={mode} />
              ) : (
                <p className="text-sm text-muted-foreground">
                  {colorsSweep.loading
                    ? "計算中…"
                    : "「計算する」を押すと結果が表示されます。"}
                </p>
              )}
            </CardContent>
          </Card>

          {(anglesSweep.result || loading) && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">角度スイープ</CardTitle>
              </CardHeader>
              <CardContent>
                {anglesSweep.result ? (
                  <AngleSweepChart sweep={anglesSweep.result} mode={mode} />
                ) : (
                  <p className="text-sm text-muted-foreground">計算中…</p>
                )}
              </CardContent>
            </Card>
          )}

          {(colorsSweep.result || colorsSweep.loading) && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">反射スペクトル</CardTitle>
              </CardHeader>
              <CardContent>
                {colorsSweep.result ? (
                  <AngleSpectraChart sweep={colorsSweep.result} mode={mode} />
                ) : (
                  <p className="text-sm text-muted-foreground">計算中…</p>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

/** 入射角ごとの見た目の色チップ(研究スライド上段の形式)。 */
function AngleColorChips({
  sweep,
  mode,
}: {
  sweep: SweepResponse;
  mode: DiffractionMode;
}) {
  return (
    <div className="flex justify-center gap-8">
      {sweep.entries.map((e) => {
        const color = entryColor(e, mode);
        return (
          <div key={e.thetaDeg} className="grid justify-items-center gap-1.5">
            <span className="text-sm font-semibold">{Math.round(e.thetaDeg)}°</span>
            <div
              className="h-16 w-16 rounded-md border"
              style={{ backgroundColor: color?.hex }}
            />
            <span className="text-xs text-muted-foreground">{color?.hex}</span>
          </div>
        );
      })}
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
    <div className="grid gap-2">
      <span className="text-sm font-semibold">{label}</span>
      <div className="grid grid-cols-2 gap-2">
        <div className="col-span-full">
          <Field label="名前">
            <Input
              value={value.name}
              onChange={(e) => onChange({ ...value, name: e.target.value })}
            />
          </Field>
        </div>
        <OpticsFields value={value} onChange={(patch) => onChange({ ...value, ...patch })} />
      </div>
    </div>
  );
}
