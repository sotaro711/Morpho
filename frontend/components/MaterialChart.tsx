"use client";

import Plot from "@/components/Plot";
import type { DispersionPoint } from "@/lib/api/client";
import { clipToRange, WL_MAX, WL_MIN } from "@/lib/dispersion";

const WAVELENGTH_AXIS = { range: [WL_MIN, WL_MAX], tick0: WL_MIN, dtick: 100 };

/**
 * 材料の n, k を、計算で使う波長の範囲について描く。上段が n、下段が k で、それぞれに波長軸を付ける。
 * 範囲内で k がすべて 0 の材料は n だけを描く。
 * カーソルを乗せるとその波長の n と k の値が出る（登録内容の確認用）。
 */
export default function MaterialChart({
  points: registered,
}: {
  points: DispersionPoint[];
}) {
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
                xaxis: "x2",
                yaxis: "y2",
                line: { color: "#dc2626", width: 2 },
                hovertemplate: "k = %{y:.4f}<extra></extra>",
              },
            ]
          : []),
      ]}
      layout={{
        autosize: true,
        height: absorbs ? 360 : 240,
        margin: { l: 56, r: 16, t: 8, b: 40 },
        hovermode: "x unified",
        xaxis: {
          ...WAVELENGTH_AXIS,
          title: { text: absorbs ? "" : "波長 (nm)" },
        },
        yaxis: {
          title: { text: "n (屈折率)" },
          domain: absorbs ? [0.58, 1] : [0, 1],
        },
        xaxis2: {
          ...WAVELENGTH_AXIS,
          title: { text: "波長 (nm)" },
          anchor: "y2",
          matches: "x",
        },
        yaxis2: {
          title: { text: "k (消衰係数)" },
          domain: [0, 0.42],
          anchor: "x2",
          rangemode: "tozero",
        },
        shapes: absorbs
          ? [
              {
                type: "line",
                xref: "paper",
                yref: "paper",
                x0: 0,
                x1: 1,
                y0: 0.475,
                y1: 0.475,
                line: { color: "#93c5fd", width: 1 },
              },
            ]
          : [],
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
