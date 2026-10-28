/**
 * x, y の 2 方向に周期を持つ構造（3 次元構造）のモデル。
 *
 * 2 つのテンプレートを持つ:
 *   - 球の配列: 正方格子の各点に球が 1 つ基板の上に載る（Mie 共鳴の構造色）
 *   - 角柱の段差: 正方格子の各点に角柱（基板上げ）があり、その上に多層膜が成膜される
 *     （stepped.ts の段差を x, y 両方向に有限な矩形にしたもの）
 *
 * RCWA は層ごとに面内一様な厚みが要るので、球は z 方向に N 枚の輪切り（各層に
 * 半径 r(z) の円領域）、角柱の多層膜は stepped.ts と同じ水平スライス（各層に
 * 矩形領域）で表す。断面図はこの計算用スライスと同じ源から作るので、表示される
 * 構造と計算される構造は常に一致する。
 *
 * React に依存しない純粋なモジュールなので "use client" は付けない。
 */

import type {
  EditableLayer,
  LayerDTO,
  SimulationRequest,
} from "@/lib/api/client";
import {
  apiOptics,
  type Medium,
  type Optics,
  type Settings,
} from "@/lib/stack";
import { columnProfile, materialAt, type Slab } from "@/lib/stepped";

export type Template3D = "sphere" | "pillar";

/**
 * 基底数（RCWA が保持する逆格子ベクトルの本数）の既定値と上限。S4 は |G| の小さい順に
 * N 本を選ぶので任意の N を指定できる。x, y とも ±M の正方形で取るなら (2M+1)²
 * （9, 25, 49, 81, 121, 169, 225）。上限はバックエンドの NUM_BASIS_LIMIT（225）。
 * 球配列の検証では 81 で 3 桁目まで収束した。計算時間は基底数のほぼ 3 乗。
 */
export const DEFAULT_NUM_BASIS_3D = 49;
export const NUM_BASIS_LIMIT_3D = 225;

export type SphereConfig = {
  /** x 方向の周期。 */
  periodNm: number;
  /** y 方向の周期。 */
  periodYNm: number;
  diameterNm: number;
  /** 球を z 方向に輪切りにする枚数。多いほど球に近いが、小さな円を表すのに高次の基底が要る。 */
  slices: number;
  numBasis: number;
  particle: Medium;
};

// 研究スライド「Si 粒子単層配置（Mie 共鳴）による青色発色」の構造。
export const DEFAULT_SPHERE: SphereConfig = {
  periodNm: 160,
  periodYNm: 160,
  diameterNm: 120,
  slices: 8,
  numBasis: DEFAULT_NUM_BASIS_3D,
  particle: { name: "Si", n: 4.0, k: 0.072 },
};

export type PillarConfig = {
  /** x 方向の周期。 */
  periodNm: number;
  /** y 方向の周期。 */
  periodYNm: number;
  /** 角柱の x 方向の幅。 */
  widthNm: number;
  /** 角柱の y 方向の奥行き。 */
  depthNm: number;
  /** 角柱の高さ（基板上げ）。 */
  raiseNm: number;
  numBasis: number;
};

// 研究スライド「3 次元段差付き多層膜」の構造（上げ高さは 2 次元の段差と同じ λ0/2）。
export const DEFAULT_PILLAR: PillarConfig = {
  periodNm: 600,
  periodYNm: 600,
  widthNm: 300,
  depthNm: 300,
  raiseNm: 235,
  numBasis: DEFAULT_NUM_BASIS_3D,
};

/** 断面図の向き。x なら y = 周期/2 を通る xz 面、y なら x = 周期/2 を通る yz 面。 */
export type SectionAxis = "x" | "y";

/** 断面図の箱。x0, x1 は断面の面内座標（x または y）、z は基板表面を 0 とする高さ。 */
export type Box = {
  x0: number;
  x1: number;
  z0: number;
  z1: number;
  name: string;
} & Optics;

/** 上面図（xy 面）の形。単位胞の左下隅を原点とする nm 座標。 */
export type TopShape =
  | {
      kind: "rect";
      cxNm: number;
      cyNm: number;
      widthNm: number;
      heightNm: number;
      name: string;
    }
  | {
      kind: "circle";
      cxNm: number;
      cyNm: number;
      radiusNm: number;
      name: string;
    };

/** 立体図の立体。単位胞の左下隅を原点、基板表面を z = 0 とする nm 座標。 */
export type Solid = (
  | {
      kind: "box";
      x0: number;
      x1: number;
      y0: number;
      y1: number;
      z0: number;
      z1: number;
    }
  | { kind: "sphere"; cx: number; cy: number; cz: number; radiusNm: number }
) & { name: string } & Optics;

// 入射媒質は空気に固定（stack.ts の規約と同じ。スライスの背景材料にも使う）。
const AIR: Medium = { name: "空気", n: 1.0, k: 0 };

function sameOptics(a: Optics, b: Optics): boolean {
  return a.materialId
    ? a.materialId === b.materialId
    : !b.materialId && a.n === b.n && a.k === b.k;
}

function airLayer(): LayerDTO {
  return { name: AIR.name, thicknessNm: 0, n: AIR.n, k: AIR.k, regions: [] };
}

function substrateLayer(substrate: Medium): LayerDTO {
  return {
    name: substrate.name,
    thicknessNm: 0,
    ...apiOptics(substrate),
    regions: [],
  };
}

// ---------------- 球の配列 ----------------

/** 球の輪切り（上から順）。z は基板表面からの高さ、radiusNm はスライス中央での半径。 */
export function sphereSlices(
  config: SphereConfig,
): { z0: number; z1: number; radiusNm: number }[] {
  const { diameterNm, slices } = config;
  const r = diameterNm / 2;
  const h = diameterNm / slices;
  return Array.from({ length: slices }, (_, i) => {
    const z1 = diameterNm - i * h;
    const z0 = z1 - h;
    const zMid = (z0 + z1) / 2;
    return {
      z0,
      z1,
      radiusNm: Math.sqrt(Math.max(r * r - (zMid - r) ** 2, 0)),
    };
  });
}

export function toSphereSimulationRequest(
  settings: Settings,
  config: SphereConfig,
  substrate: Medium,
): SimulationRequest {
  const { periodNm, periodYNm, particle } = config;
  const layers: LayerDTO[] = [
    airLayer(),
    ...sphereSlices(config).map((s, i) => ({
      name: `slice${i}`,
      thicknessNm: s.z1 - s.z0,
      n: AIR.n,
      k: AIR.k,
      regions: [
        {
          shape: "circle" as const,
          cxNm: periodNm / 2,
          cyNm: periodYNm / 2,
          radiusNm: s.radiusNm,
          ...apiOptics(particle),
        },
      ],
    })),
    substrateLayer(substrate),
  ];
  return {
    ...settings,
    thetaDeg: 0,
    numBasis: config.numBasis,
    periodNm,
    periodYNm,
    layers,
  };
}

/** 上面図: 球の最大断面（赤道）の円。 */
export function sphereTopShapes(config: SphereConfig): TopShape[] {
  return [
    {
      kind: "circle",
      cxNm: config.periodNm / 2,
      cyNm: config.periodYNm / 2,
      radiusNm: config.diameterNm / 2,
      name: config.particle.name,
    },
  ];
}

export function sphereBoxes(
  config: SphereConfig,
  axis: SectionAxis = "x",
): Box[] {
  const cx = (axis === "x" ? config.periodNm : config.periodYNm) / 2;
  return sphereSlices(config).map((s) => ({
    x0: cx - s.radiusNm,
    x1: cx + s.radiusNm,
    z0: s.z0,
    z1: s.z1,
    ...config.particle,
  }));
}

/** 立体図: 輪切りではなく本物の球として描く。 */
export function sphereSolids(config: SphereConfig): Solid[] {
  const r = config.diameterNm / 2;
  return [
    {
      kind: "sphere",
      cx: config.periodNm / 2,
      cy: config.periodYNm / 2,
      cz: r,
      radiusNm: r,
      ...config.particle,
    },
  ];
}

// ---------------- 角柱の段差 ----------------

/** 角柱の列（上げ）と周囲の平らな列。x の範囲は単位胞の中央に角柱を置く。 */
function pillarColumns(
  config: PillarConfig,
  films: EditableLayer[],
  substrate: Medium,
) {
  const x0 = (config.periodNm - config.widthNm) / 2;
  return {
    raised: {
      x0,
      x1: x0 + config.widthNm,
      prof: columnProfile(films, substrate, true, config.raiseNm),
    },
    flat: { prof: columnProfile(films, substrate, false, config.raiseNm) },
  };
}

export function toPillarSimulationRequest(
  settings: Settings,
  config: PillarConfig,
  films: EditableLayer[],
  substrate: Medium,
): SimulationRequest {
  const { raised, flat } = pillarColumns(config, films, substrate);

  // 両方の列の層境界を集めて z 方向のスライスを作る（stepped.ts と同じ）
  const breaks = new Set<number>([0]);
  for (const prof of [raised.prof, flat.prof]) {
    let z = 0;
    for (const slab of prof) {
      z += slab.thicknessNm;
      breaks.add(Math.round(z * 1e6) / 1e6);
    }
  }
  const zs = [...breaks].sort((a, b) => a - b);

  // 各スライスは「平らな列の材料」を背景に、角柱の列の材料を矩形領域として重ねる
  const layers: LayerDTO[] = [airLayer()];
  for (let i = zs.length - 2; i >= 0; i--) {
    const zMid = (zs[i] + zs[i + 1]) / 2;
    const background: Slab = materialAt(flat.prof, zMid) ?? {
      ...AIR,
      thicknessNm: 0,
    };
    const top = materialAt(raised.prof, zMid);
    const regions =
      top && !sameOptics(top, background)
        ? [
            {
              shape: "rect" as const,
              cxNm: config.periodNm / 2,
              cyNm: config.periodYNm / 2,
              widthNm: config.widthNm,
              heightNm: config.depthNm,
              ...apiOptics(top),
            },
          ]
        : [];
    layers.push({
      name: `slice${i}`,
      thicknessNm: zs[i + 1] - zs[i],
      ...apiOptics(background),
      regions,
    });
  }
  layers.push(substrateLayer(substrate));

  return {
    ...settings,
    thetaDeg: 0,
    numBasis: config.numBasis,
    periodNm: config.periodNm,
    periodYNm: config.periodYNm,
    layers,
  };
}

/** 上面図: 角柱の矩形（多層膜は角柱の上に同じ形で載るので輪郭は角柱と同じ）。 */
export function pillarTopShapes(
  config: PillarConfig,
  substrate: Medium,
): TopShape[] {
  return [
    {
      kind: "rect",
      cxNm: config.periodNm / 2,
      cyNm: config.periodYNm / 2,
      widthNm: config.widthNm,
      heightNm: config.depthNm,
      name: `${substrate.name} の角柱`,
    },
  ];
}

export function pillarBoxes(
  config: PillarConfig,
  films: EditableLayer[],
  substrate: Medium,
  axis: SectionAxis = "x",
): Box[] {
  const { raised, flat } = pillarColumns(config, films, substrate);
  // yz 断面では角柱の奥行きと y 方向の周期で切る
  const period = axis === "x" ? config.periodNm : config.periodYNm;
  const size = axis === "x" ? config.widthNm : config.depthNm;
  const x0 = (period - size) / 2;
  const x1 = x0 + size;
  const boxes: Box[] = [];
  const stack = (prof: Slab[], x0: number, x1: number) => {
    let z = 0;
    for (const slab of prof) {
      boxes.push({ x0, x1, z0: z, z1: z + slab.thicknessNm, ...slab });
      z += slab.thicknessNm;
    }
  };
  stack(flat.prof, 0, x0);
  stack(raised.prof, x0, x1);
  stack(flat.prof, x1, period);
  return boxes;
}

/**
 * 立体図: 角柱の上に多層膜を積み、周囲の平らな多層膜は角柱を囲む 4 本の帯で表す
 * （穴あきの板を 1 つの立体にすると描画が面倒なので分ける）。
 */
export function pillarSolids(
  config: PillarConfig,
  films: EditableLayer[],
  substrate: Medium,
): Solid[] {
  const { raised, flat } = pillarColumns(config, films, substrate);
  const { periodNm: px, periodYNm: py, widthNm: w, depthNm: d } = config;
  const x0 = (px - w) / 2;
  const x1 = x0 + w;
  const y0 = (py - d) / 2;
  const y1 = y0 + d;
  const solids: Solid[] = [];
  const stack = (
    prof: Slab[],
    rect: { x0: number; x1: number; y0: number; y1: number },
  ) => {
    let z = 0;
    for (const slab of prof) {
      solids.push({
        kind: "box",
        ...rect,
        z0: z,
        z1: z + slab.thicknessNm,
        ...slab,
      });
      z += slab.thicknessNm;
    }
  };
  // 周囲の帯は x 方向の 2 本を周期いっぱい、y 方向の 2 本を角柱の幅に合わせる
  stack(flat.prof, { x0: 0, x1: px, y0: 0, y1: y0 });
  stack(flat.prof, { x0: 0, x1: px, y0: y1, y1: py });
  stack(flat.prof, { x0: 0, x1: x0, y0, y1 });
  stack(flat.prof, { x0: x1, x1: px, y0, y1 });
  stack(raised.prof, { x0, x1, y0, y1 });
  return solids;
}
