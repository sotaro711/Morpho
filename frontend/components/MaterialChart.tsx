"use client";

import Plot from "@/components/Plot";
import type { DispersionPoint } from "@/lib/api/client";
import { clipToRange, WL_MAX, WL_MIN } from "@/lib/dispersion";

export default function MaterialChart({ points: registered }: { points: DispersionPoint[] }) {
  const points = clipToRange(registered);
  const x = points.map((p) => p.wavelengthNm);
  const absorbs = points.some((p) => p.k > 0);
  return (
    <Plot
      data={[
        {
          x,
          y: points.map((p) => p.n),
          name: "n",
          type: "scatter",
          mode: "lines",
          line: { color: "#000000", width: 2 },
          hovertemplate: "n = %{y:.4f}<extra></extra>",
        },
        ...(absorbs
          ? [
              {
                x,
                y: points.map((p) => p.k),
                name: "k",
                type: "scatter" as const,
                mode: "lines" as const,
                yaxis: "y2",
                line: { color: "#dc2626", width: 2 },
                hovertemplate: "k = %{y:.4f}<extra></extra>",
              },
            ]
          : []),
      ]}
      layout={{
        autosize: true,
        height: 240,
        margin: { l: 48, r: absorbs ? 48 : 16, t: 8, b: 40 },
        hovermode: "x unified",
        xaxis: { title: { text: "波長 (nm)" }, range: [WL_MIN, WL_MAX], tick0: WL_MIN, dtick: 100 },
        yaxis: { title: { text: "n" } },
        yaxis2: {
          title: { text: "k" },
          overlaying: "y",
          side: "right",
          rangemode: "tozero",
          tickfont: { color: "#dc2626" },
        },
        showlegend: false,
        paper_bgcolor: "#ffffff",
        plot_bgcolor: "#ffffff",
      }}
      useResizeHandler
      style={{ width: "100%" }}
      config={{ displayModeBar: false, responsive: true }}
    />
  );
}
