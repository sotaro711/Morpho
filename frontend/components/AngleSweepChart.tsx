"use client";

import Plot from "@/components/Plot";
import type { SweepResponse } from "@/lib/api/client";

/** 折れ線の色。おおまかに「その波長が単色光として見える色」に寄せる(スライドの配色)。 */
export function wavelengthColor(wlNm: number): string {
  if (wlNm < 430) return "#7c3aed"; // 紫
  if (wlNm < 500) return "#2563eb"; // 青
  if (wlNm < 565) return "#16a34a"; // 緑
  if (wlNm < 625) return "#d9a406"; // 黄
  return "#dc2626"; // 赤
}

/**
 * 角度スイープチャート(研究スライド上段の形式)。
 * 波長ごとに 1 本の折れ線(x = 入射角、y = その波長の全反射率)。
 */
export default function AngleSweepChart({ sweep }: { sweep: SweepResponse }) {
  return (
    <Plot
      data={sweep.wavelengths.map((wl, wi) => ({
        x: sweep.entries.map((e) => e.thetaDeg),
        y: sweep.entries.map((e) => e.R[wi]),
        name: `${Math.round(wl)} nm`,
        type: "scatter" as const,
        mode: "lines" as const,
        line: { color: wavelengthColor(wl), width: wl >= 430 && wl < 500 ? 3 : 2 },
      }))}
      layout={{
        autosize: true,
        height: 360,
        margin: { l: 56, r: 16, t: 16, b: 48 },
        xaxis: { title: { text: "入射角 (deg)" }, range: [-85, 85], dtick: 20 },
        yaxis: { title: { text: "反射率 R" }, range: [0, 1] },
        legend: { orientation: "h", y: -0.25 },
      }}
      useResizeHandler
      style={{ width: "100%" }}
      config={{ displayModeBar: false, responsive: true }}
    />
  );
}
