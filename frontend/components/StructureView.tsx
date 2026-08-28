"use client";

import type { Annotations, Shape } from "plotly.js";

import Plot from "@/components/Plot";
import type { LayerDTO } from "@/lib/api/client";
import type { StructureColumn } from "@/lib/stepped";

// 構造の2次元断面図（横軸=位置, 縦軸=高さ）。入力の層データだけから描く（API 不要）。
// stepped が渡されたら段付きモード: カラムごとの矩形を実寸の x 座標で描く。

const PALETTE = [
  "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
  "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
];

// 平面多層膜には面内の周期が無いので、断面図の横幅は表示用の公称値を使う。
const DISPLAY_WIDTH = 100;

export default function StructureView({
  layers,
  stepped,
}: {
  layers: LayerDTO[];
  stepped?: { periodNm: number; columns: StructureColumn[] };
}) {
  if (stepped && stepped.columns.length > 0) {
    // 基板は layers の末尾（structureLayers の規約）。名前を段付き表示にも引き継ぐ。
    const substrateName = layers[layers.length - 1]?.name ?? "基板";
    return (
      <SteppedView
        periodNm={stepped.periodNm}
        columns={stepped.columns}
        substrateName={substrateName}
      />
    );
  }
  return <PlanarView layers={layers} />;
}

/** 段付きモード: 1 周期分の断面をカラムごとに実寸で描く。 */
function SteppedView({
  periodNm,
  columns,
  substrateName,
}: {
  periodNm: number;
  columns: StructureColumn[];
  substrateName: string;
}) {
  // 材料名 → 色。平面モードと同じく膜(上の層)から順に割り当て、基板は最後。
  // 基板上げの台座は基板と同じ名前なので、自動的に同じ色になる。
  const names = new Set<string>();
  // slabs は下→上の順なので、平面モード(上の層から順)と同じ割り当てになるよう反転して走査する
  for (const c of columns) for (const s of [...c.slabs].reverse()) names.add(s.name);
  names.delete(substrateName);
  names.add(substrateName);
  const colorOf = new Map<string, string>();
  [...names].forEach((m, i) => colorOf.set(m, PALETTE[i % PALETTE.length]));

  const maxTop = Math.max(
    ...columns.map((c) => {
      const last = c.slabs[c.slabs.length - 1];
      return last ? last.zNm + last.thicknessNm : 0;
    }),
  );
  const subH = Math.max(maxTop * 0.15, 60); // 半無限の基板は名目高さで描く

  const shapes: Partial<Shape>[] = [
    rect(0, 0, periodNm, subH, colorOf.get(substrateName)!),
  ];
  for (const c of columns) {
    for (const slab of c.slabs) {
      shapes.push(
        rect(
          c.xNm,
          subH + slab.zNm,
          c.xNm + c.widthNm,
          subH + slab.zNm + slab.thicknessNm,
          colorOf.get(slab.name) ?? "#cccccc",
        ),
      );
    }
  }

  const annotations: Partial<Annotations>[] = [
    {
      x: periodNm / 2,
      y: subH / 2,
      text: substrateName,
      showarrow: false,
      font: { color: "#ffffff", size: 11 },
    },
  ];

  return (
    <Plot
      data={[]}
      layout={{
        autosize: true,
        height: 320,
        margin: { l: 48, r: 16, t: 8, b: 40 },
        xaxis: {
          title: { text: "位置 (nm) — 1 周期分" },
          range: [0, periodNm],
          zeroline: false,
        },
        yaxis: {
          title: { text: "高さ (nm)" },
          range: [0, subH + maxTop * 1.05],
          zeroline: false,
        },
        shapes,
        annotations,
        plot_bgcolor: "#ffffff",
      }}
      useResizeHandler
      style={{ width: "100%" }}
      config={{ displayModeBar: false, responsive: true }}
    />
  );
}

/** 平面モード: 従来どおり全層を横幅いっぱいの帯として描く。 */
function PlanarView({ layers }: { layers: LayerDTO[] }) {
  // 材料名 → 色 のマップ。
  const materials = new Set<string>();
  for (const l of layers) {
    materials.add(l.name);
  }
  const colorOf = new Map<string, string>();
  [...materials].forEach((m, i) => colorOf.set(m, PALETTE[i % PALETTE.length]));

  // 表示用の各層の高さ。半無限層（厚さ0）には名目高さを与える。
  const finiteSum = layers.reduce((s, l) => s + (l.thicknessNm > 0 ? l.thicknessNm : 0), 0);
  const nominal = Math.max(finiteSum * 0.25, 60);
  const dispH = (l: LayerDTO) => (l.thicknessNm > 0 ? l.thicknessNm : nominal);

  const total = layers.reduce((s, l) => s + dispH(l), 0);

  const shapes: Partial<Shape>[] = [];
  const annotations: Partial<Annotations>[] = [];

  let top = total; // 先頭（入射側）を一番上に描く
  for (const layer of layers) {
    const h = dispH(layer);
    const y0 = top - h;
    const y1 = top;
    const bg = colorOf.get(layer.name) ?? "#cccccc";

    shapes.push(rect(0, y0, DISPLAY_WIDTH, y1, bg));

    annotations.push({
      x: DISPLAY_WIDTH / 2,
      y: (y0 + y1) / 2,
      text: `${layer.name}${layer.thicknessNm > 0 ? ` (${layer.thicknessNm}nm)` : ""}`,
      showarrow: false,
      font: { color: "#ffffff", size: 11 },
    });

    top = y0;
  }

  return (
    <Plot
      data={[]}
      layout={{
        autosize: true,
        height: 320,
        margin: { l: 48, r: 16, t: 8, b: 40 },
        // 平面多層膜なので横方向は意味を持たない。軸は隠す。
        xaxis: { range: [0, DISPLAY_WIDTH], zeroline: false, showticklabels: false },
        yaxis: { title: { text: "高さ (nm)" }, range: [0, total], zeroline: false },
        shapes,
        annotations,
        plot_bgcolor: "#ffffff",
      }}
      useResizeHandler
      style={{ width: "100%" }}
      config={{ displayModeBar: false, responsive: true }}
    />
  );
}

function rect(
  x0: number,
  y0: number,
  x1: number,
  y1: number,
  color: string,
): Partial<Shape> {
  return {
    type: "rect",
    x0,
    y0,
    x1,
    y1,
    fillcolor: color,
    line: { color: "#333333", width: 1 },
  };
}
