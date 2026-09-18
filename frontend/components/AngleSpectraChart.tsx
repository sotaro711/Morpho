"use client";

import Plot from "@/components/Plot";
import type { SweepResponse } from "@/lib/api/client";
import {
  entryReflectance,
  reflectanceAxisLabel,
  type DiffractionMode,
} from "@/lib/diffraction";

/** 入射角ごとの線色(研究スライドの配色: 0° 黒 / 30° 橙 / 60° 緑)。 */
function thetaColor(thetaDeg: number): string {
  if (thetaDeg < 15) return "#111111";
  if (thetaDeg < 45) return "#ea8c3c";
  return "#16a34a";
}

/**
 * 角度別スペクトルチャート(研究スライド下段の形式)。
 * 入射角ごとに 1 本の折れ線(x = 波長、y = 反射率)。
 */
export default function AngleSpectraChart({
  sweep,
  mode = "zeroth",
}: {
  sweep: SweepResponse;
  mode?: DiffractionMode;
}) {
  return (
    <Plot
      data={sweep.entries.map((e) => ({
        x: sweep.wavelengths,
        y: entryReflectance(e, mode),
        name: `${Math.round(e.thetaDeg)}°`,
        type: "scatter" as const,
        mode: "lines" as const,
        line: { color: thetaColor(e.thetaDeg), width: e.thetaDeg === 0 ? 3 : 2 },
      }))}
      layout={{
        autosize: true,
        height: 360,
        margin: { l: 56, r: 16, t: 16, b: 48 },
        xaxis: { title: { text: "波長 (nm)" } },
        yaxis: { title: { text: reflectanceAxisLabel(mode) }, range: [0, 1] },
        legend: { orientation: "h", y: -0.25 },
      }}
      useResizeHandler
      style={{ width: "100%" }}
      config={{ displayModeBar: false, responsive: true }}
    />
  );
}
