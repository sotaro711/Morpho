"use client";

import type { Annotations, Shape } from "plotly.js";

import { useMaterials } from "@/components/MaterialsProvider";
import Plot from "@/components/Plot";
import type { LayerDTO } from "@/lib/api/client";
import type { Box, SectionAxis, TopShape } from "@/lib/lattice3d";
import type { StructureColumn } from "@/lib/stepped";

// 構造の2次元断面図（横軸=位置, 縦軸=高さ）。入力の層データだけから描く（API 不要）。
// stepped が渡されたら段付きモード: カラムごとの矩形を実寸の x 座標で描く。

const PALETTE = [
  "#1f77b4",
  "#ff7f0e",
  "#2ca02c",
  "#d62728",
  "#9467bd",
  "#8c564b",
  "#e377c2",
  "#7f7f7f",
  "#bcbd22",
  "#17becf",
];

// 平面多層膜には面内の周期が無いので、断面図の横幅は表示用の公称値を使う。
const DISPLAY_WIDTH = 100;

// materialId があれば登録した材料（波長分散）で、n, k は使わない。
type Optical = {
  name: string;
  n?: number | null;
  k: number;
  materialId?: string | null;
};

// 材料 id → 材料名。
type MaterialNames = Map<string, string>;

// 色分けのキー。名前ではなく光学定数で分けることで、同じ材料のつもりで
// n や k を打ち間違えた層が別色になり、入力ミスに気づけるようにする(#33)。
// 登録した材料は材料ごとに 1 色にする。
function materialKey({ n, k, materialId }: Optical): string {
  return materialId ? `material:${materialId}` : `${n ?? "?"}|${k}`;
}

// 出現順にパレットを割り当てる。キーの重複は最初の出現位置を優先する。
function assignColors(keys: Iterable<string>): Map<string, string> {
  const colorOf = new Map<string, string>();
  for (const key of keys) {
    if (!colorOf.has(key))
      colorOf.set(key, PALETTE[colorOf.size % PALETTE.length]);
  }
  return colorOf;
}

function formatIndex(
  { name, n, k, materialId }: Optical,
  names: MaterialNames,
): string {
  if (materialId) {
    const materialName = names.get(materialId);
    // 層名が材料名と同じなら繰り返さない。
    if (materialName === undefined) return "削除された材料";
    return materialName === name ? "登録した材料" : `材料: ${materialName}`;
  }
  const nText = n ?? "?";
  return k > 0 ? `n=${nText}, k=${k}` : `n=${nText}`;
}

export default function StructureView({
  layers,
  stepped,
}: {
  layers: LayerDTO[];
  stepped?: { periodNm: number; columns: StructureColumn[] };
}) {
  const { materials } = useMaterials();
  const names: MaterialNames = new Map(materials.map((m) => [m.id, m.name]));
  if (stepped && stepped.columns.length > 0) {
    // 基板は layers の末尾（structureLayers の規約）。段付き表示にも引き継ぐ。
    const substrate = layers[layers.length - 1] ?? { name: "基板", n: 1, k: 0 };
    return (
      <SteppedView
        periodNm={stepped.periodNm}
        columns={stepped.columns}
        substrate={substrate}
        names={names}
      />
    );
  }
  return <PlanarView layers={layers} names={names} />;
}

/** 段付きモード: 1 周期分の断面をカラムごとに実寸で描く。 */
function SteppedView({
  periodNm,
  columns,
  substrate,
  names,
}: {
  periodNm: number;
  columns: StructureColumn[];
  substrate: Optical;
  names: MaterialNames;
}) {
  // 光学定数 → 色。平面モードと同じく膜(上の層)から順に割り当て、基板は最後。
  // 基板上げの台座は基板と同じ光学定数なので、自動的に同じ色になる。
  const substrateKey = materialKey(substrate);
  const keys: string[] = [];
  // slabs は下→上の順なので、平面モード(上の層から順)と同じ割り当てになるよう反転して走査する
  for (const c of columns) {
    for (const s of [...c.slabs].reverse()) {
      const key = materialKey(s);
      if (key !== substrateKey) keys.push(key);
    }
  }
  keys.push(substrateKey);
  const colorOf = assignColors(keys);

  const maxTop = Math.max(
    ...columns.map((c) => {
      const last = c.slabs[c.slabs.length - 1];
      return last ? last.zNm + last.thicknessNm : 0;
    }),
  );
  const subH = Math.max(maxTop * 0.15, 60); // 半無限の基板は名目高さで描く

  const shapes: Partial<Shape>[] = [
    rect(0, 0, periodNm, subH, colorOf.get(substrateKey)!),
  ];
  for (const c of columns) {
    for (const slab of c.slabs) {
      shapes.push(
        rect(
          c.xNm,
          subH + slab.zNm,
          c.xNm + c.widthNm,
          subH + slab.zNm + slab.thicknessNm,
          colorOf.get(materialKey(slab)) ?? "#cccccc",
        ),
      );
    }
  }

  const annotations: Partial<Annotations>[] = [
    {
      x: periodNm / 2,
      y: subH / 2,
      text: `${substrate.name} (${formatIndex(substrate, names)})`,
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

/**
 * 3 次元構造の断面（y = 周期/2 の xz 面）。箱の並びをそのまま実寸で描く。
 * 球の輪切りや角柱の多層膜など、カラムに分けられない形のための汎用版。
 */
export function CrossSectionView({
  periodNm,
  boxes,
  substrate,
  axis = "x",
}: {
  periodNm: number;
  boxes: Box[];
  substrate: Optical;
  axis?: SectionAxis;
}) {
  const { materials } = useMaterials();
  const names: MaterialNames = new Map(materials.map((m) => [m.id, m.name]));
  // 色は上の箱から順に割り当て、基板は最後（平面・段付きと同じ規約）。
  const substrateKey = materialKey(substrate);
  const ordered = [...boxes].sort((a, b) => b.z1 - a.z1);
  const colorOf = assignColors([
    ...ordered.map(materialKey).filter((key) => key !== substrateKey),
    substrateKey,
  ]);

  const maxTop = Math.max(0, ...boxes.map((b) => b.z1));
  const subH = Math.max(maxTop * 0.15, 60); // 半無限の基板は名目高さで描く

  const shapes: Partial<Shape>[] = [
    rect(0, 0, periodNm, subH, colorOf.get(substrateKey)!),
    ...boxes.map((b) =>
      rect(
        b.x0,
        subH + b.z0,
        b.x1,
        subH + b.z1,
        colorOf.get(materialKey(b)) ?? "#cccccc",
      ),
    ),
  ];
  const annotations: Partial<Annotations>[] = [
    {
      x: periodNm / 2,
      y: subH / 2,
      text: `${substrate.name} (${formatIndex(substrate, names)})`,
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
          title: {
            text:
              axis === "x"
                ? "x (nm) — 入射面 xz での断面"
                : "y (nm) — 入射面 yz での断面",
          },
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

/**
 * 3 次元構造の上面図（xy 面）。単位胞 1 つを軸なしで描き、周期と形の寸法を
 * 寸法線で、入射面を中央を通る線で示す（研究スライドの図に合わせた体裁）。
 */
export function TopView({
  periodNm,
  periodYNm,
  shapes,
  phiDeg = 0,
}: {
  periodNm: number;
  periodYNm: number;
  shapes: TopShape[];
  phiDeg?: number;
}) {
  // 寸法線の間隔は単位胞の大きさに比例させ、周期を変えても見た目を保つ
  const unit = Math.max(periodNm, periodYNm) * 0.12;
  const plotShapes: Partial<Shape>[] = [
    {
      type: "rect",
      x0: 0,
      y0: 0,
      x1: periodNm,
      y1: periodYNm,
      line: { color: "#333333", width: 1.5 },
    },
  ];
  const annotations: Partial<Annotations>[] = [];

  // 寸法線（JIS Z 8317 に倣う）: 両端矢印、数値は水平なら線の上、垂直なら線の左に
  // 下から上へ読む向きで置く。単位は図の隅に一括で注記するので数値のみ。
  function dimension(
    x0: number,
    y0: number,
    x1: number,
    y1: number,
    label: string,
  ) {
    const horizontal = y0 === y1;
    annotations.push({
      x: x1,
      y: y1,
      ax: x0,
      ay: y0,
      axref: "x",
      ayref: "y",
      xref: "x",
      yref: "y",
      text: "",
      showarrow: true,
      // plotly は "end+start" を受けるが型定義に無い
      arrowside: "end+start" as Annotations["arrowside"],
      arrowhead: 2,
      arrowsize: 0.8,
      arrowwidth: 1,
      arrowcolor: "#333333",
    });
    annotations.push({
      x: (x0 + x1) / 2,
      y: (y0 + y1) / 2,
      text: label,
      showarrow: false,
      font: { size: 11, color: "#333333" },
      xanchor: horizontal ? "center" : "right",
      yanchor: horizontal ? "bottom" : "middle",
      xshift: horizontal ? 0 : -3,
      yshift: horizontal ? 2 : 0,
      textangle: horizontal ? "0" : "-90",
    });
  }
  // 寸法補助線: 対象の辺から少し離して始め、寸法線を少し越えるまで伸ばす
  const gap = unit * 0.15;
  const over = unit * 0.25;
  function extensionY(x: number, yEdge: number, yDim: number) {
    const dir = Math.sign(yDim - yEdge);
    thinLine(x, yEdge + gap * dir, x, yDim + over * dir, "solid");
  }
  function extensionX(y: number, xEdge: number, xDim: number) {
    const dir = Math.sign(xDim - xEdge);
    thinLine(xEdge + gap * dir, y, xDim + over * dir, y, "solid");
  }
  function thinLine(
    x0: number,
    y0: number,
    x1: number,
    y1: number,
    dash: "solid" | "dashdot",
  ) {
    plotShapes.push({
      type: "line",
      x0,
      y0,
      x1,
      y1,
      line: { color: "#999999", width: 0.5, dash },
    });
  }

  // 中心線（一点鎖線）
  const cx = periodNm / 2;
  const cy = periodYNm / 2;
  thinLine(cx, -gap * 2, cx, periodYNm + gap * 2, "dashdot");
  thinLine(-gap * 2, cy, periodNm + gap * 2, cy, "dashdot");

  // 周期: x は上側、y は右側。大きい寸法ほど外側に置く
  const topY = periodYNm + unit * 2;
  const rightX = periodNm + unit * 2;
  extensionY(0, periodYNm, topY);
  extensionY(periodNm, periodYNm, topY);
  dimension(0, topY, periodNm, topY, `${periodNm}`);
  extensionX(0, periodNm, rightX);
  extensionX(periodYNm, periodNm, rightX);
  dimension(rightX, 0, rightX, periodYNm, `${periodYNm}`);

  // 形: 円は直径 φ を上側に 1 本、矩形は幅を上側・奥行きを右側（どちらも周期の内側）に。
  // 左と下は入射の矢印のために空けておく。
  for (const s of shapes) {
    const w = s.kind === "circle" ? s.radiusNm * 2 : s.widthNm;
    const h = s.kind === "circle" ? s.radiusNm * 2 : s.heightNm;
    const x0 = s.cxNm - w / 2;
    const x1 = s.cxNm + w / 2;
    const y0 = s.cyNm - h / 2;
    const y1 = s.cyNm + h / 2;
    plotShapes.push({
      type: s.kind === "circle" ? "circle" : "rect",
      x0,
      y0,
      x1,
      y1,
      fillcolor: PALETTE[0],
      line: { color: "#333333", width: 1 },
    });
    const sizeY = periodYNm + unit;
    extensionY(x0, y1, sizeY);
    extensionY(x1, y1, sizeY);
    dimension(x0, sizeY, x1, sizeY, s.kind === "circle" ? `φ${w}` : `${w}`);
    if (s.kind === "rect") {
      const sizeX = periodNm + unit;
      extensionX(y0, x1, sizeX);
      extensionX(y1, x1, sizeX);
      dimension(sizeX, y0, sizeX, y1, `${h}`);
    }
  }

  // 単位の注記（寸法数値には付けない）
  annotations.push({
    x: rightX,
    y: -unit,
    text: "単位 nm",
    showarrow: false,
    font: { size: 10, color: "#666666" },
    xanchor: "right",
    yanchor: "top",
  });

  // 入射面: x 軸から φ だけ回った向きの線。単位胞の外（ラベル側）から反対側の辺まで引く
  const phi = (phiDeg * Math.PI) / 180;
  const dir = { x: Math.cos(phi), y: Math.sin(phi) };
  const half = Math.min(
    Math.abs(dir.x) > 1e-9 ? periodNm / 2 / Math.abs(dir.x) : Infinity,
    Math.abs(dir.y) > 1e-9 ? periodYNm / 2 / Math.abs(dir.y) : Infinity,
  );
  const tail = half + unit * 1.2;
  plotShapes.push({
    type: "line",
    x0: cx - dir.x * tail,
    y0: cy - dir.y * tail,
    x1: cx + dir.x * half,
    y1: cy + dir.y * half,
    line: { color: "#e6b800", width: 3 },
  });
  // φ ≠ 0 のときは基準（φ = 0°、x 方向）を点線で添えて、何からの角度か分かるようにする
  if (phiDeg !== 0) {
    plotShapes.push({
      type: "line",
      x0: cx - tail,
      y0: cy,
      x1: periodNm,
      y1: cy,
      line: { color: "#e6b800", width: 1.5, dash: "dot" },
    });
    annotations.push({
      x: cx - tail - unit * 0.3,
      y: cy,
      text: "基準 φ = 0°",
      showarrow: false,
      font: { size: 10, color: "#8a6d00" },
      xanchor: "right",
      yanchor: "middle",
    });
  }
  const anchor = (c: number, near: string, far: string, mid: string) =>
    c > 0.3 ? near : c < -0.3 ? far : mid;
  annotations.push({
    x: cx - dir.x * (tail + unit * 0.3),
    y: cy - dir.y * (tail + unit * 0.3),
    text: `入射面 φ = ${phiDeg}°`,
    showarrow: false,
    font: { size: 12, color: "#8a6d00" },
    xanchor: anchor(dir.x, "right", "left", "center") as "right",
    yanchor: anchor(dir.y, "top", "bottom", "middle") as "top",
  });

  return (
    <Plot
      data={[]}
      layout={{
        autosize: true,
        height: 320,
        margin: { l: 8, r: 8, t: 8, b: 8 },
        xaxis: {
          visible: false,
          range: [-unit * 5, periodNm + unit * 3.5],
          fixedrange: true,
        },
        yaxis: {
          visible: false,
          range: [-unit * 3, periodYNm + unit * 3.5],
          fixedrange: true,
          // 上面図は x, y を同じ縮尺で描く（正方形が正方形に見えるように）
          scaleanchor: "x",
          scaleratio: 1,
        },
        shapes: plotShapes,
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
function PlanarView({
  layers,
  names,
}: {
  layers: LayerDTO[];
  names: MaterialNames;
}) {
  const colorOf = assignColors(layers.map(materialKey));

  // 表示用の各層の高さ。半無限層（厚さ0）には名目高さを与える。
  const finiteSum = layers.reduce(
    (s, l) => s + (l.thicknessNm > 0 ? l.thicknessNm : 0),
    0,
  );
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
    const bg = colorOf.get(materialKey(layer)) ?? "#cccccc";

    shapes.push(rect(0, y0, DISPLAY_WIDTH, y1, bg));

    annotations.push({
      x: DISPLAY_WIDTH / 2,
      y: (y0 + y1) / 2,
      text: `${layer.name} (${layer.thicknessNm > 0 ? `${layer.thicknessNm}nm, ` : ""}${formatIndex(layer, names)})`,
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
        xaxis: {
          range: [0, DISPLAY_WIDTH],
          zeroline: false,
          showticklabels: false,
        },
        yaxis: {
          title: { text: "高さ (nm)" },
          range: [0, total],
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
