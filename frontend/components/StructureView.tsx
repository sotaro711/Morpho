"use client";

import type { Annotations, PlotData, Shape } from "plotly.js";

import { useMaterials } from "@/components/MaterialsProvider";
import Plot from "@/components/Plot";
import type { LayerDTO } from "@/lib/api/client";
import type { Box, SectionAxis, Solid, TopShape } from "@/lib/lattice3d";
import type { StructureColumn } from "@/lib/stepped";

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

const DISPLAY_WIDTH = 100;

type Optical = {
  name: string;
  n?: number | null;
  k: number;
  materialId?: string | null;
};

type MaterialNames = Map<string, string>;

function materialKey({ n, k, materialId }: Optical): string {
  return materialId ? `material:${materialId}` : `${n ?? "?"}|${k}`;
}

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
  const substrateKey = materialKey(substrate);
  const keys: string[] = [];
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
  const subH = Math.max(maxTop * 0.15, 60);

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

export function CrossSectionView({
  periodNm,
  boxes,
  substrate,
  axis = "x",
  repeat = 1,
  extent,
}: {
  periodNm: number;
  boxes: Box[];
  substrate: Optical;
  axis?: SectionAxis;
  repeat?: number;
  extent?: [number, number] | null;
}) {
  const { materials } = useMaterials();
  const names: MaterialNames = new Map(materials.map((m) => [m.id, m.name]));
  const substrateKey = materialKey(substrate);
  const ordered = [...boxes].sort((a, b) => b.z1 - a.z1);
  const colorOf = assignColors([
    ...ordered.map(materialKey).filter((key) => key !== substrateKey),
    substrateKey,
  ]);

  const maxTop = Math.max(0, ...boxes.map((b) => b.z1));
  const subH = Math.max(maxTop * 0.15, 60);

  const joinsSubstrate = (b: Box) =>
    materialKey(b) === substrateKey &&
    b.z0 === 0 &&
    b.x0 <= 0 &&
    b.x1 >= periodNm;
  const substrateTop =
    subH + Math.max(0, ...boxes.filter(joinsSubstrate).map((b) => b.z1));

  const span = periodNm * repeat;
  const cells = Array.from({ length: repeat }, (_, i) => i * periodNm);
  const shapes: Partial<Shape>[] = [
    rect(0, 0, span, substrateTop, colorOf.get(substrateKey)!),
    ...boxes
      .filter((b) => !joinsSubstrate(b))
      .flatMap((b) => {
        const color = colorOf.get(materialKey(b)) ?? "#cccccc";
        return b.x0 <= 0 && b.x1 >= periodNm
          ? [rect(0, subH + b.z0, span, subH + b.z1, color)]
          : cells.map((dx) =>
              rect(b.x0 + dx, subH + b.z0, b.x1 + dx, subH + b.z1, color),
            );
      }),
  ];
  const annotations: Partial<Annotations>[] = [
    {
      x: span / 2,
      y: subH / 2,
      text: `${substrate.name} (${formatIndex(substrate, names)})`,
      showarrow: false,
      font: { color: "#ffffff", size: 11 },
    },
  ];

  for (const x of cells.slice(1)) {
    shapes.push({
      type: "line",
      x0: x,
      y0: 0,
      x1: x,
      y1: subH + maxTop * 1.05,
      line: CELL_LINE,
    });
  }

  const gapNm = extent ? periodNm - (extent[1] - extent[0]) : 0;
  const showGap = repeat > 1 && extent != null && gapNm > 0;
  if (showGap) {
    const mid = Math.floor((repeat - 1) / 2) * periodNm;
    const x0 = extent[1] + mid;
    const x1 = extent[0] + mid + periodNm;
    const yDim = subH + maxTop * 1.1;
    for (const x of [x0, x1]) {
      shapes.push({
        type: "line",
        x0: x,
        y0: subH,
        x1: x,
        y1: yDim + maxTop * 0.03,
        line: { color: "#999999", width: 0.5 },
      });
    }
    annotations.push(...dimensionLine(x0, yDim, x1, yDim, formatNm(gapNm)));
  }

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
          range: [0, span],
          zeroline: false,
          constrain: "domain",
        },
        yaxis: {
          title: { text: "高さ (nm)" },
          range: [0, subH + maxTop * (showGap ? 1.25 : 1.05)],
          zeroline: false,
          scaleanchor: "x",
          scaleratio: 1,
          constrain: "domain",
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

function dimensionLine(
  x0: number,
  y0: number,
  x1: number,
  y1: number,
  label: string,
): Partial<Annotations>[] {
  const horizontal = y0 === y1;
  return [
    {
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
    },
    {
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
    },
  ];
}

function formatNm(v: number): string {
  return `${Number(v.toFixed(1))}`;
}

const CELL_LINE = {
  color: "rgba(0, 0, 0, 0.35)",
  width: 1,
  dash: "dot",
} as const;

const SOLID_VIEW_CELL_NM = 450;

const TOP_VIEW_FRAME_NM = 600;

export function SolidView({
  periodNm,
  periodYNm,
  solids,
  substrate,
  repeat = 1,
}: {
  periodNm: number;
  periodYNm: number;
  solids: Solid[];
  substrate: Optical;
  repeat?: number;
}) {
  const { materials } = useMaterials();
  const names: MaterialNames = new Map(materials.map((m) => [m.id, m.name]));
  const substrateKey = materialKey(substrate);
  const ordered = [...solids].sort((a, b) => solidTop(b) - solidTop(a));
  const colorOf = assignColors([
    ...ordered.map(materialKey).filter((key) => key !== substrateKey),
    substrateKey,
  ]);

  const maxTop = Math.max(0, ...solids.map(solidTop));
  const subH = Math.max(maxTop * 0.15, 60);

  const spanX = periodNm * repeat;
  const spanY = periodYNm * repeat;
  const frame = Math.max(SOLID_VIEW_CELL_NM * repeat, spanX, spanY);
  const padX = (frame - spanX) / 2;
  const padY = (frame - spanY) / 2;
  const dims = [frame, frame, subH + maxTop];
  // 軸の範囲どおりの実寸比で描く。aspectmode "data" は範囲ではなくデータの広がりで
  // 比を決めるので、余白を取ると歪む。最長辺を 1 にそろえて視点は固定する。
  const longest = Math.max(...dims);
  const aspectratio = {
    x: dims[0] / longest,
    y: dims[1] / longest,
    z: dims[2] / longest,
  };
  const eye = { x: 0.95, y: -1.2, z: 0.6 };

  const dtick = tickStep(Math.max(spanX, spanY, subH + maxTop));
  const ticks = (span: number) =>
    Array.from({ length: Math.floor(span / dtick) }, (_, i) => (i + 1) * dtick);

  const shown = new Set<string>();
  const legendName = (o: Optical) => `${o.name} (${formatIndex(o, names)})`;
  const mesh = (
    key: string,
    name: string,
    m: Mesh,
    translucent = false,
  ): Partial<PlotData> => {
    const first = !shown.has(key);
    shown.add(key);
    const { smooth, ...geometry } = m;
    // color / flatshading / lighting は mesh3d 固有で型定義に無い
    const trace: Mesh3DTrace = {
      type: "mesh3d",
      ...geometry,
      color: colorOf.get(key) ?? "#cccccc",
      opacity: translucent ? 0.3 : 1,
      flatshading: !smooth,
      lighting: { ambient: 0.6, diffuse: 0.8, specular: 0.1, roughness: 0.6 },
      name,
      legendgroup: key,
      showlegend: first,
      hoverinfo: "name",
    };
    return trace as Partial<PlotData>;
  };

  const fillsCell = (s: Solid) =>
    s.kind === "box" &&
    s.x0 <= 0 &&
    s.x1 >= periodNm &&
    s.y0 <= 0 &&
    s.y1 >= periodYNm;
  const joinsSubstrate = (s: Solid) =>
    fillsCell(s) &&
    !!s.translucent &&
    materialKey(s) === substrateKey &&
    s.kind === "box" &&
    s.z0 === 0;
  const joined = ordered.filter(joinsSubstrate);
  const substrateTop = subH + Math.max(0, ...joined.map(solidTop));
  const cells = Array.from({ length: repeat * repeat }, (_, i) => ({
    dx: (i % repeat) * periodNm,
    dy: Math.floor(i / repeat) * periodYNm,
  }));
  const meshesOf = (s: Solid): Mesh[] => {
    if (s.kind === "sphere")
      return cells.map(({ dx, dy }) =>
        sphereMesh(s.cx + dx, s.cy + dy, subH + s.cz, s.radiusNm),
      );
    if (fillsCell(s))
      return [boxMesh(0, spanX, 0, spanY, subH + s.z0, subH + s.z1)];
    return cells.map(({ dx, dy }) =>
      boxMesh(
        s.x0 + dx,
        s.x1 + dx,
        s.y0 + dy,
        s.y1 + dy,
        subH + s.z0,
        subH + s.z1,
      ),
    );
  };
  const data: Partial<PlotData>[] = [
    mesh(
      substrateKey,
      legendName(substrate),
      boxMesh(0, spanX, 0, spanY, 0, substrateTop),
      joined.length > 0,
    ),
    ...ordered
      .filter((s) => !joinsSubstrate(s))
      .flatMap((s) =>
        meshesOf(s).map((m) =>
          mesh(materialKey(s), legendName(s), m, s.translucent),
        ),
      ),
  ];
  if (repeat > 1) {
    const x: (number | null)[] = [];
    const y: (number | null)[] = [];
    for (let i = 1; i < repeat; i++) {
      x.push(i * periodNm, i * periodNm, null, 0, spanX, null);
      y.push(0, spanY, null, i * periodYNm, i * periodYNm, null);
    }
    data.push({
      type: "scatter3d",
      mode: "lines",
      x,
      y,
      z: x.map((v) => (v === null ? null : substrateTop + 0.5)),
      line: { color: "rgba(0, 0, 0, 0.6)", width: 3 },
      showlegend: false,
      hoverinfo: "skip",
    });
  }

  return (
    <Plot
      data={data}
      layout={{
        autosize: true,
        height: 400,
        margin: { l: 0, r: 0, t: 0, b: 0 },
        scene: {
          aspectmode: "manual",
          aspectratio,
          camera: { eye },
          xaxis: {
            title: { text: "x (nm)" },
            range: [-padX, spanX + padX],
            tickvals: ticks(spanX),
          },
          yaxis: {
            title: { text: "y (nm)" },
            range: [-padY, spanY + padY],
            tickvals: ticks(spanY),
          },
          zaxis: {
            title: { text: "高さ (nm)" },
            range: [0, subH + maxTop],
            dtick,
          },
        },
        legend: { orientation: "h", y: 0, font: { size: 11 } },
        showlegend: true,
      }}
      useResizeHandler
      style={{ width: "100%" }}
      config={{ displayModeBar: false, responsive: true }}
    />
  );
}

function tickStep(span: number): number {
  const raw = span / 6;
  const pow = 10 ** Math.floor(Math.log10(raw));
  return pow * ([1, 2, 5].find((m) => m * pow >= raw) ?? 10);
}

function solidTop(s: Solid): number {
  return s.kind === "box" ? s.z1 : s.cz + s.radiusNm;
}

type Mesh = {
  x: number[];
  y: number[];
  z: number[];
  i: Int32Array;
  j: Int32Array;
  k: Int32Array;
  smooth?: boolean;
};

type Mesh3DTrace = Partial<Omit<PlotData, "i" | "j" | "k">> &
  Mesh & {
    color: string;
    flatshading: boolean;
    lighting: {
      ambient: number;
      diffuse: number;
      specular: number;
      roughness: number;
    };
  };

function triangles(tris: number[][]): Pick<Mesh, "i" | "j" | "k"> {
  return {
    i: Int32Array.from(tris, (t) => t[0]),
    j: Int32Array.from(tris, (t) => t[1]),
    k: Int32Array.from(tris, (t) => t[2]),
  };
}

const BOX_TRIANGLES = [
  [0, 2, 1],
  [0, 3, 2],
  [4, 5, 6],
  [4, 6, 7],
  [0, 1, 5],
  [0, 5, 4],
  [1, 2, 6],
  [1, 6, 5],
  [2, 3, 7],
  [2, 7, 6],
  [3, 0, 4],
  [3, 4, 7],
];

function boxMesh(
  x0: number,
  x1: number,
  y0: number,
  y1: number,
  z0: number,
  z1: number,
): Mesh {
  return {
    x: [x0, x1, x1, x0, x0, x1, x1, x0],
    y: [y0, y0, y1, y1, y0, y0, y1, y1],
    z: [z0, z0, z0, z0, z1, z1, z1, z1],
    ...triangles(BOX_TRIANGLES),
  };
}

function sphereMesh(cx: number, cy: number, cz: number, r: number): Mesh {
  const rings = 16;
  const segments = 24;
  const x: number[] = [];
  const y: number[] = [];
  const z: number[] = [];
  for (let i = 0; i <= rings; i++) {
    const polar = (Math.PI * i) / rings;
    for (let j = 0; j < segments; j++) {
      const az = (2 * Math.PI * j) / segments;
      x.push(cx + r * Math.sin(polar) * Math.cos(az));
      y.push(cy + r * Math.sin(polar) * Math.sin(az));
      z.push(cz + r * Math.cos(polar));
    }
  }
  const at = (i: number, j: number) => i * segments + (j % segments);
  const tris: number[][] = [];
  for (let i = 0; i < rings; i++) {
    for (let j = 0; j < segments; j++) {
      tris.push([at(i, j), at(i + 1, j), at(i + 1, j + 1)]);
      tris.push([at(i, j), at(i + 1, j + 1), at(i, j + 1)]);
    }
  }
  return { x, y, z, ...triangles(tris), smooth: true };
}

export function TopView({
  periodNm,
  periodYNm,
  shapes,
  phiDeg = 0,
  repeat = 1,
}: {
  periodNm: number;
  periodYNm: number;
  shapes: TopShape[];
  phiDeg?: number;
  repeat?: number;
}) {
  const spanX = periodNm * repeat;
  const spanY = periodYNm * repeat;
  const frame = Math.max(TOP_VIEW_FRAME_NM, spanX, spanY);
  const unit = frame * 0.12;
  const plotShapes: Partial<Shape>[] = [
    {
      type: "rect",
      x0: 0,
      y0: 0,
      x1: spanX,
      y1: spanY,
      line: { color: "#333333", width: 1.5 },
    },
  ];
  const annotations: Partial<Annotations>[] = [];

  function dimension(
    x0: number,
    y0: number,
    x1: number,
    y1: number,
    label: string,
  ) {
    annotations.push(...dimensionLine(x0, y0, x1, y1, label));
  }
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

  for (let i = 1; i < repeat; i++) {
    const x = i * periodNm;
    const y = i * periodYNm;
    plotShapes.push(
      { type: "line", x0: x, y0: 0, x1: x, y1: spanY, line: CELL_LINE },
      { type: "line", x0: 0, y0: y, x1: spanX, y1: y, line: CELL_LINE },
    );
  }

  const cx = spanX / 2;
  const cy = spanY / 2;
  thinLine(cx, -gap * 2, cx, spanY + gap * 2, "dashdot");
  thinLine(-gap * 2, cy, spanX + gap * 2, cy, "dashdot");

  const topY = spanY + unit * 3;
  const rightX = spanX + unit * 3;
  extensionY(0, spanY, topY);
  extensionY(periodNm, spanY, topY);
  dimension(0, topY, periodNm, topY, `${periodNm}`);
  extensionX(0, spanX, rightX);
  extensionX(periodYNm, spanX, rightX);
  dimension(rightX, 0, rightX, periodYNm, `${periodYNm}`);

  const lastX = (repeat - 1) * periodNm;
  const lastY = (repeat - 1) * periodYNm;
  const sizeY = spanY + unit * 1.5;
  const sizeX = spanX + unit * 1.5;
  const bounds = { x0: Infinity, x1: -Infinity, y0: Infinity, y1: -Infinity };
  for (const s of shapes) {
    const w = s.kind === "circle" ? s.radiusNm * 2 : s.widthNm;
    const h = s.kind === "circle" ? s.radiusNm * 2 : s.heightNm;
    const x0 = s.cxNm - w / 2;
    const x1 = s.cxNm + w / 2;
    const y0 = s.cyNm - h / 2;
    const y1 = s.cyNm + h / 2;
    bounds.x0 = Math.min(bounds.x0, x0);
    bounds.x1 = Math.max(bounds.x1, x1);
    bounds.y0 = Math.min(bounds.y0, y0);
    bounds.y1 = Math.max(bounds.y1, y1);
    for (let i = 0; i < repeat; i++) {
      for (let j = 0; j < repeat; j++) {
        plotShapes.push({
          type: s.kind === "circle" ? "circle" : "rect",
          x0: x0 + i * periodNm,
          y0: y0 + j * periodYNm,
          x1: x1 + i * periodNm,
          y1: y1 + j * periodYNm,
          fillcolor: PALETTE[0],
          line: { color: "#333333", width: 1 },
        });
      }
    }
    extensionY(x0, y1 + lastY, sizeY);
    extensionY(x1, y1 + lastY, sizeY);
    dimension(x0, sizeY, x1, sizeY, s.kind === "circle" ? `φ${w}` : `${w}`);
    if (s.kind === "rect") {
      extensionX(y0, x1 + lastX, sizeX);
      extensionX(y1, x1 + lastX, sizeX);
      dimension(sizeX, y0, sizeX, y1, `${h}`);
    }
  }

  if (repeat > 1 && shapes.length > 0) {
    const gapX = periodNm - (bounds.x1 - bounds.x0);
    if (gapX > 0) {
      extensionY(bounds.x1, bounds.y1 + lastY, sizeY);
      extensionY(bounds.x0 + periodNm, bounds.y1 + lastY, sizeY);
      dimension(bounds.x1, sizeY, bounds.x0 + periodNm, sizeY, formatNm(gapX));
    }
    const gapY = periodYNm - (bounds.y1 - bounds.y0);
    if (gapY > 0) {
      extensionX(bounds.y1, bounds.x1 + lastX, sizeX);
      extensionX(bounds.y0 + periodYNm, bounds.x1 + lastX, sizeX);
      dimension(sizeX, bounds.y1, sizeX, bounds.y0 + periodYNm, formatNm(gapY));
    }
  }

  annotations.push({
    x: rightX,
    y: -unit,
    text: "単位 nm",
    showarrow: false,
    font: { size: 10, color: "#666666" },
    xanchor: "right",
    yanchor: "top",
  });

  const phi = (phiDeg * Math.PI) / 180;
  const dir = { x: Math.cos(phi), y: Math.sin(phi) };
  const half = Math.min(
    Math.abs(dir.x) > 1e-9 ? spanX / 2 / Math.abs(dir.x) : Infinity,
    Math.abs(dir.y) > 1e-9 ? spanY / 2 / Math.abs(dir.y) : Infinity,
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
  if (phiDeg !== 0) {
    plotShapes.push({
      type: "line",
      x0: cx - tail,
      y0: cy,
      x1: spanX,
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
        height: 440,
        margin: { l: 8, r: 8, t: 8, b: 8 },
        xaxis: {
          visible: false,
          range: [-unit * 5, frame + unit * 4.5],
          fixedrange: true,
        },
        yaxis: {
          visible: false,
          range: [-unit * 3, frame + unit * 4.5],
          fixedrange: true,
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

function PlanarView({
  layers,
  names,
}: {
  layers: LayerDTO[];
  names: MaterialNames;
}) {
  const colorOf = assignColors(layers.map(materialKey));

  const finiteSum = layers.reduce(
    (s, l) => s + (l.thicknessNm > 0 ? l.thicknessNm : 0),
    0,
  );
  const nominal = Math.max(finiteSum * 0.25, 60);
  const dispH = (l: LayerDTO) => (l.thicknessNm > 0 ? l.thicknessNm : nominal);

  const total = layers.reduce((s, l) => s + dispH(l), 0);

  const shapes: Partial<Shape>[] = [];
  const annotations: Partial<Annotations>[] = [];

  let top = total;
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
