"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

import { AngleColorChips } from "@/components/AngleColorChips";
import { DiffractionModeToggle } from "@/components/DiffractionModeToggle";
import { Field } from "@/components/Field";
import { LayerEditor } from "@/components/LayerEditor";
import { NumberInput } from "@/components/NumberInput";
import { OpticsFields } from "@/components/OpticsFields";
import { PairInsertForm } from "@/components/PairInsertForm";
import { SettingsForm } from "@/components/SettingsForm";
import { useSimulator3D } from "@/components/Simulator3DProvider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { saveResult } from "@/lib/api/client";
import { hasDiffractionModes } from "@/lib/diffraction";
import {
  NUM_BASIS_LIMIT_3D,
  pillarBoxes,
  pillarTopShapes,
  sphereBoxes,
  sphereTopShapes,
  toPillarSimulationRequest,
  toSphereSimulationRequest,
  type PillarConfig,
  type SectionAxis,
  type SphereConfig,
  type Template3D,
} from "@/lib/lattice3d";
import type { Medium, Settings } from "@/lib/stack";

// Plotly はブラウザ専用なので SSR を無効化して読み込む。
const CrossSectionView = dynamic(
  () => import("@/components/StructureView").then((m) => m.CrossSectionView),
  { ssr: false },
);
const TopView = dynamic(
  () => import("@/components/StructureView").then((m) => m.TopView),
  {
    ssr: false,
  },
);
const AngleSweepChart = dynamic(() => import("@/components/AngleSweepChart"), {
  ssr: false,
});
const AngleSpectraChart = dynamic(
  () => import("@/components/AngleSpectraChart"),
  {
    ssr: false,
  },
);

// 見た目の色・角度別スペクトル用: 0/30/60°、波長は 10nm 間隔(色変換できる間隔)。
const COLOR_THETAS = [0, 30, 60];
const COLOR_SWEEP_WL = { wlMin: 380, wlMax: 780, wlPoints: 41 };
// 角度スイープチャート用: 2 次元ページと同じ -80〜80° を 10° 刻み、代表 5 波長。
const ANGLE_THETAS = Array.from({ length: 17 }, (_, i) => -80 + i * 10);
const ANGLE_SWEEP_WL = { wavelengthsNm: [400, 470, 540, 600, 700] };

const TEMPLATES: { value: Template3D; label: string; description: string }[] = [
  {
    value: "sphere",
    label: "球の配列",
    description: "正方格子の各点に球が 1 つ基板の上に載る（Mie 共鳴の構造色）",
  },
  {
    value: "pillar",
    label: "角柱の段差",
    description:
      "正方格子の各点に角柱（基板上げ）があり、その上に多層膜を成膜する",
  },
];

export default function Lattice3DPage() {
  const sim = useSimulator3D();
  const {
    template,
    settings,
    setSettings,
    mode,
    setMode,
    colorsSweep,
    anglesSweep,
  } = sim;
  const [saveError, setSaveError] = useState<string | null>(null);
  const loading = colorsSweep.loading || anglesSweep.loading;
  const error = colorsSweep.error ?? anglesSweep.error;

  const patchSettings = (p: Partial<Settings>) =>
    setSettings((s) => ({ ...s, ...p }));

  const buildRequest = () =>
    template === "sphere"
      ? toSphereSimulationRequest(settings, sim.sphere, sim.sphereSubstrate)
      : toPillarSimulationRequest(
          settings,
          sim.pillar,
          sim.pillarFilms,
          sim.pillarSubstrate,
        );

  const runSimulation = async () => {
    const base = buildRequest();
    // 2 次元ページと同じく直列に実行し、両方そろったら履歴に保存する。
    anglesSweep.clear();
    setSaveError(null);
    const colors = await colorsSweep.run({
      ...base,
      ...COLOR_SWEEP_WL,
      thetaDegs: COLOR_THETAS,
      includeColors: true,
    });
    const angles = await anglesSweep.run({
      ...base,
      ...ANGLE_SWEEP_WL,
      thetaDegs: ANGLE_THETAS,
      includeColors: false,
    });
    if (!colors || !angles) return;
    try {
      await saveResult({ request: base, colors, angles });
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : String(e));
    }
  };

  // 入射面（φ=0 なら xz 面、90 なら yz 面）。断面図もこの面で切る。
  const axis: SectionAxis = settings.phiDeg === 90 ? "y" : "x";
  const periodNm =
    template === "sphere" ? sim.sphere.periodNm : sim.pillar.periodNm;
  const periodYNm =
    template === "sphere" ? sim.sphere.periodYNm : sim.pillar.periodYNm;
  const sectionPeriodNm = axis === "x" ? periodNm : periodYNm;
  const topShapes =
    template === "sphere"
      ? sphereTopShapes(sim.sphere)
      : pillarTopShapes(sim.pillar, sim.pillarSubstrate);
  const substrate =
    template === "sphere" ? sim.sphereSubstrate : sim.pillarSubstrate;
  const boxes =
    template === "sphere"
      ? sphereBoxes(sim.sphere, axis)
      : pillarBoxes(sim.pillar, sim.pillarFilms, sim.pillarSubstrate, axis);
  const numBasis =
    template === "sphere" ? sim.sphere.numBasis : sim.pillar.numBasis;

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-6">
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(420px,460px)_1fr]">
        {/* 左：入力 */}
        <div className="grid min-w-0 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">構造</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3">
              <Field label="テンプレート">
                <Select
                  value={template}
                  onValueChange={(v) => sim.setTemplate(v as Template3D)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TEMPLATES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <p className="text-xs text-muted-foreground">
                {TEMPLATES.find((t) => t.value === template)?.description}
                。x, y の 2 方向に周期をもって並ぶ。
              </p>
              {template === "sphere" ? (
                <SphereForm value={sim.sphere} onChange={sim.setSphere} />
              ) : (
                <PillarForm value={sim.pillar} onChange={sim.setPillar} />
              )}
            </CardContent>
          </Card>

          {template === "pillar" && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">角柱の上の多層膜</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-3">
                  <LayerEditor
                    layers={sim.pillarFilms}
                    onChange={sim.setPillarFilms}
                  />
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">
                    ペアをまとめて挿入
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <PairInsertForm
                    onInsert={(block) =>
                      sim.setPillarFilms((prev) => [...block, ...prev])
                    }
                  />
                </CardContent>
              </Card>
            </>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">基板</CardTitle>
            </CardHeader>
            <CardContent>
              <MediumFields
                value={substrate}
                onChange={
                  template === "sphere"
                    ? sim.setSphereSubstrate
                    : sim.setPillarSubstrate
                }
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">計算条件</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3">
              <SettingsForm value={settings} onChange={patchSettings} />
              <Field label="入射面（光が入ってくる向き）">
                <Select
                  value={String(settings.phiDeg)}
                  onValueChange={(v) => patchSettings({ phiDeg: Number(v) })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0">x 方向（xz 面、φ = 0°）</SelectItem>
                    <SelectItem value="90">y 方向（yz 面、φ = 90°）</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <p className="text-xs text-muted-foreground">
                基底数 {numBasis}。計算時間は基底数のほぼ 3 乗で増える。
              </p>
            </CardContent>
          </Card>

          <div className="sticky bottom-0 z-10 grid gap-3 border-t bg-background/85 py-3 backdrop-blur">
            <Button
              onClick={runSimulation}
              disabled={loading}
              className="w-full"
            >
              {loading ? "計算中…（数十秒〜数分）" : "計算する"}
            </Button>
            {error && (
              <div
                role="alert"
                className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive"
              >
                エラー: {error}
              </div>
            )}
            {saveError && (
              <p role="status" className="text-xs text-muted-foreground">
                結果を保存できませんでした: {saveError}
              </p>
            )}
          </div>
        </div>

        {/* 右：構造の断面図（常時）とスペクトル（計算後） */}
        <div className="grid min-w-0 gap-6 lg:sticky lg:top-6 lg:self-start">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                構造（断面図と上面図）
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4">
              <CrossSectionView
                periodNm={sectionPeriodNm}
                boxes={boxes}
                substrate={substrate}
                axis={axis}
              />
              <TopView
                periodNm={periodNm}
                periodYNm={periodYNm}
                shapes={topShapes}
                phiDeg={settings.phiDeg}
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

function NumBasisField({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div
      className="grid gap-1"
      title={`計算に含めるフーリエ基底（回折次数）の本数。最大 ${NUM_BASIS_LIMIT_3D}。x, y とも ±M で取るなら (2M+1)² = 9, 25, 49, 81, 121, 169, 225。上げると精度が上がるが、計算時間はほぼ 3 乗で増える`}
    >
      <Label className="text-xs text-muted-foreground">
        基底数（回折次数の本数）
      </Label>
      <NumberInput
        step={1}
        min={1}
        max={NUM_BASIS_LIMIT_3D}
        value={value}
        onChange={(v) =>
          onChange(Math.min(NUM_BASIS_LIMIT_3D, Math.max(1, Math.round(v))))
        }
      />
    </div>
  );
}

function SphereForm({
  value,
  onChange,
}: {
  value: SphereConfig;
  onChange: (v: SphereConfig) => void;
}) {
  const patch = (p: Partial<SphereConfig>) => onChange({ ...value, ...p });
  return (
    <div className="grid grid-cols-2 gap-2">
      <Field label="周期 x (nm)">
        <NumberInput
          step={10}
          min={1}
          value={value.periodNm}
          onChange={(periodNm) => patch({ periodNm })}
        />
      </Field>
      <Field label="周期 y (nm)">
        <NumberInput
          step={10}
          min={1}
          value={value.periodYNm}
          onChange={(periodYNm) => patch({ periodYNm })}
        />
      </Field>
      <Field label="球の直径 (nm)">
        <NumberInput
          step={10}
          min={1}
          value={value.diameterNm}
          onChange={(diameterNm) => patch({ diameterNm })}
        />
      </Field>
      <Field label="輪切りの枚数">
        <NumberInput
          step={1}
          min={1}
          max={64}
          value={value.slices}
          onChange={(v) =>
            patch({ slices: Math.min(64, Math.max(1, Math.round(v))) })
          }
        />
      </Field>
      <NumBasisField
        value={value.numBasis}
        onChange={(numBasis) => patch({ numBasis })}
      />
      <div className="col-span-full border-t pt-2">
        <MediumFields
          label="球の材料"
          value={value.particle}
          onChange={(particle) => patch({ particle })}
        />
      </div>
      {value.diameterNm > Math.min(value.periodNm, value.periodYNm) && (
        <p className="col-span-full text-xs text-destructive">
          球の直径が周期を超えています（隣の球と重なる）
        </p>
      )}
    </div>
  );
}

function PillarForm({
  value,
  onChange,
}: {
  value: PillarConfig;
  onChange: (v: PillarConfig) => void;
}) {
  const patch = (p: Partial<PillarConfig>) => onChange({ ...value, ...p });
  return (
    <div className="grid grid-cols-2 gap-2">
      <Field label="周期 x (nm)">
        <NumberInput
          step={10}
          min={1}
          value={value.periodNm}
          onChange={(periodNm) => patch({ periodNm })}
        />
      </Field>
      <Field label="周期 y (nm)">
        <NumberInput
          step={10}
          min={1}
          value={value.periodYNm}
          onChange={(periodYNm) => patch({ periodYNm })}
        />
      </Field>
      <Field label="角柱の幅 x (nm)">
        <NumberInput
          step={10}
          min={1}
          value={value.widthNm}
          onChange={(widthNm) => patch({ widthNm })}
        />
      </Field>
      <Field label="角柱の奥行き y (nm)">
        <NumberInput
          step={10}
          min={1}
          value={value.depthNm}
          onChange={(depthNm) => patch({ depthNm })}
        />
      </Field>
      <Field label="上げ高さ (nm)">
        <NumberInput
          step={1}
          min={0}
          value={value.raiseNm}
          onChange={(raiseNm) => patch({ raiseNm })}
        />
      </Field>
      <NumBasisField
        value={value.numBasis}
        onChange={(numBasis) => patch({ numBasis })}
      />
      {(value.widthNm > value.periodNm || value.depthNm > value.periodYNm) && (
        <p className="col-span-full text-xs text-destructive">
          角柱が周期を超えています（隣の角柱と重なる）
        </p>
      )}
    </div>
  );
}

/** 名前 + 光学定数（材料選択つき）。基板や球の材料に使う。 */
function MediumFields({
  label,
  value,
  onChange,
}: {
  label?: string;
  value: Medium;
  onChange: (v: Medium) => void;
}) {
  return (
    <div className="grid gap-2">
      {label && <span className="text-sm font-semibold">{label}</span>}
      <div className="grid grid-cols-2 gap-2">
        <div className="col-span-full">
          <Field label="名前">
            <Input
              value={value.name}
              onChange={(e) => onChange({ ...value, name: e.target.value })}
            />
          </Field>
        </div>
        <OpticsFields
          value={value}
          onChange={(patch) => onChange({ ...value, ...patch })}
        />
      </div>
    </div>
  );
}
