"use client";

import Plot from "@/components/Plot";
import type { DispersionPoint } from "@/lib/api/client";

/**
 * 材料の n, k を波長に対して描く。n は左軸、k は右軸。
 * カーソルを乗せるとその波長の n と k の値が出る（登録内容の確認用）。
 */
export default function MaterialChart({ points }: { points: DispersionPoint[] }) {
  const x = points.map((p) => p.wavelengthNm);
  const hasAbsorption = points.some((p) => p.k > 0);
  return (
    <Plot
      data={[
        {
          x,
          y: points.map((p) => p.n),
          name: "n",
          type: "scatter",
          mode: "lines",
          line: { color: "#2563eb", width: 2 },
          hovertemplate: "n = %{y:.4f}<extra></extra>",
        },
        {
          x,
          y: points.map((p) => p.k),
          name: "k",
          type: "scatter",
          mode: "lines",
          yaxis: "y2",
          line: { color: "#dc2626", width: 2, dash: hasAbsorption ? "solid" : "dot" },
          hovertemplate: "k = %{y:.4f}<extra></extra>",
        },
      ]}
      layout={{
        autosize: true,
        height: 240,
        margin: { l: 48, r: 48, t: 8, b: 40 },
        hovermode: "x unified",
        xaxis: { title: { text: "波長 (nm)" } },
        yaxis: { title: { text: "n" }, tickfont: { color: "#2563eb" } },
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
