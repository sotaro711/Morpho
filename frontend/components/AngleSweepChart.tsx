"use client";

import Plot from "@/components/Plot";
import type { SweepResponse } from "@/lib/api/client";
import {
  entryReflectance,
  reflectanceAxisLabel,
  type DiffractionMode,
} from "@/lib/diffraction";

export function wavelengthColor(wlNm: number): string {
  if (wlNm < 430) return "#7c3aed";
  if (wlNm < 500) return "#2563eb";
  if (wlNm < 565) return "#16a34a";
  if (wlNm < 625) return "#d9a406";
  return "#dc2626";
}

export default function AngleSweepChart({
  sweep,
  mode = "zeroth",
}: {
  sweep: SweepResponse;
  mode?: DiffractionMode;
}) {
  return (
    <Plot
      data={sweep.wavelengths.map((wl, wi) => ({
        x: sweep.entries.map((e) => e.thetaDeg),
        y: sweep.entries.map((e) => entryReflectance(e, mode)[wi]),
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
        yaxis: { title: { text: reflectanceAxisLabel(mode) }, range: [0, 1] },
        legend: { orientation: "h", y: -0.25 },
      }}
      useResizeHandler
      style={{ width: "100%" }}
      config={{ displayModeBar: false, responsive: true }}
    />
  );
}
