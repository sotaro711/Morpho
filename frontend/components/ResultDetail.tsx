"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

import { AngleColorChips } from "@/components/AngleColorChips";
import { DiffractionModeToggle } from "@/components/DiffractionModeToggle";
import { useMaterials } from "@/components/MaterialsProvider";
import type { LayerDTO, ResultDetail as Detail, SimulationRequest } from "@/lib/api/client";
import { hasDiffractionModes, type DiffractionMode } from "@/lib/diffraction";

// Plotly はブラウザ専用なので SSR を無効化して読み込む。
const AngleSweepChart = dynamic(() => import("@/components/AngleSweepChart"), { ssr: false });
const AngleSpectraChart = dynamic(() => import("@/components/AngleSpectraChart"), { ssr: false });

/** 履歴の 1 件の計算条件（読み取り専用）と結果。 */
export function ResultDetail({ result }: { result: Detail }) {
  const [mode, setMode] = useState<DiffractionMode>("zeroth");

  return (
    <div className="grid gap-4">
      <Conditions request={result.request} />

      {hasDiffractionModes(result.colors) && (
        <DiffractionModeToggle value={mode} onChange={setMode} />
      )}
      <Section title="見た目の色">
        <AngleColorChips sweep={result.colors} mode={mode} />
      </Section>
      <Section title="角度スイープ">
        <AngleSweepChart sweep={result.angles} mode={mode} />
      </Section>
      <Section title="反射スペクトル">
        <AngleSpectraChart sweep={result.colors} mode={mode} />
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-2">
      <h3 className="text-sm font-semibold">{title}</h3>
      {children}
    </div>
  );
}

/**
 * 計算条件。層の先頭は入射側の空気、末尾は基板。
 * 段差ありの構造は保存形式が z 方向のスライスなので、スライスごとに x 方向の区間を並べる。
 */
function Conditions({ request }: { request: SimulationRequest }) {
  const { materials } = useMaterials();
  // 材料は名前を持たないので、今の材料一覧から引く。削除・改名されていれば分からない。
  const optics = ({ n, k, materialId }: Pick<LayerDTO, "n" | "k" | "materialId">) =>
    materialId
      ? (materials.find((m) => m.id === materialId)?.name ?? "削除された材料")
      : `n=${n}, k=${k}`;
  const films = request.layers.slice(1, -1);
  const substrate = request.layers[request.layers.length - 1];
  const stepped = request.periodNm != null;

  return (
    <Section title="計算条件">
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-muted-foreground">波長</dt>
        <dd>
          {request.wlMin}–{request.wlMax} nm（{request.wlPoints} 点）
        </dd>
        <dt className="text-muted-foreground">偏光</dt>
        <dd>{request.pol}</dd>
        {stepped && (
          <>
            <dt className="text-muted-foreground">周期</dt>
            <dd>{request.periodNm} nm</dd>
          </>
        )}
        <dt className="text-muted-foreground">{stepped ? "スライス" : "膜"}</dt>
        <dd>
          {films.length === 0 ? (
            "なし"
          ) : (
            <ol className="grid gap-0.5">
              {films.map((layer, i) => (
                <li key={i}>
                  {stepped
                    ? `${layer.thicknessNm} nm: ` +
                      layer.regions
                        .map((r) => `x ${r.xNm}–${r.xNm + r.widthNm} nm ${optics(r)}`)
                        .join(" / ")
                    : `${layer.name} ${layer.thicknessNm} nm（${optics(layer)}）`}
                </li>
              ))}
            </ol>
          )}
        </dd>
        <dt className="text-muted-foreground">基板</dt>
        <dd>
          {substrate.name}（{optics(substrate)}）
        </dd>
      </dl>
    </Section>
  );
}
