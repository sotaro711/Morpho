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

export const DEFAULT_NUM_BASIS_3D = 49;
export const NUM_BASIS_LIMIT_3D = 225;

export type SphereConfig = {
  periodNm: number;
  periodYNm: number;
  diameterNm: number;
  slices: number;
  numBasis: number;
  particle: Medium;
  resin: ResinConfig;
};

export type ResinConfig = {
  enabled: boolean;
  medium: Medium;
  topNm: number;
};

export const DEFAULT_SPHERE: SphereConfig = {
  periodNm: 160,
  periodYNm: 160,
  diameterNm: 120,
  slices: 20,
  numBasis: DEFAULT_NUM_BASIS_3D,
  particle: { name: "Si", n: 4.0, k: 0.072 },
  resin: { enabled: false, medium: { name: "樹脂", n: 1.5, k: 0 }, topNm: 120 },
};

export type PillarConfig = {
  periodNm: number;
  periodYNm: number;
  widthNm: number;
  depthNm: number;
  raiseNm: number;
  numBasis: number;
};

export const DEFAULT_PILLAR: PillarConfig = {
  periodNm: 600,
  periodYNm: 600,
  widthNm: 300,
  depthNm: 300,
  raiseNm: 235,
  numBasis: DEFAULT_NUM_BASIS_3D,
};

export type SectionAxis = "x" | "y";

export type Box = {
  x0: number;
  x1: number;
  z0: number;
  z1: number;
  name: string;
} & Optics;

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
) & {
  name: string;
  translucent?: boolean;
} & Optics;

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
  const { periodNm, periodYNm, particle, resin } = config;
  const surrounding = resin.enabled ? resin.medium : AIR;
  const layers: LayerDTO[] = [
    airLayer(),
    ...(resin.enabled && resin.topNm > 0
      ? [
          {
            name: resin.medium.name,
            thicknessNm: resin.topNm,
            ...apiOptics(resin.medium),
            regions: [],
          },
        ]
      : []),
    ...sphereSlices(config).map((s, i) => ({
      name: `slice${i}`,
      thicknessNm: s.z1 - s.z0,
      ...apiOptics(surrounding),
      // 周囲と同じ材料の円は置かない（コントラスト 0 の領域があると S4 の解が壊れる）
      regions: sameOptics(particle, surrounding)
        ? []
        : [
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
  const period = axis === "x" ? config.periodNm : config.periodYNm;
  const cx = period / 2;
  const { resin } = config;
  return [
    ...(resin.enabled
      ? [
          {
            x0: 0,
            x1: period,
            z0: 0,
            z1: config.diameterNm + resin.topNm,
            ...resin.medium,
          },
        ]
      : []),
    ...sphereSlices(config).map((s) => ({
      x0: cx - s.radiusNm,
      x1: cx + s.radiusNm,
      z0: s.z0,
      z1: s.z1,
      ...config.particle,
    })),
  ];
}

export function sphereSolids(config: SphereConfig): Solid[] {
  const r = config.diameterNm / 2;
  const { resin } = config;
  return [
    {
      kind: "sphere",
      cx: config.periodNm / 2,
      cy: config.periodYNm / 2,
      cz: r,
      radiusNm: r,
      ...config.particle,
    },
    ...(resin.enabled
      ? [
          {
            kind: "box" as const,
            x0: 0,
            x1: config.periodNm,
            y0: 0,
            y1: config.periodYNm,
            z0: 0,
            z1: config.diameterNm + resin.topNm,
            translucent: true,
            ...resin.medium,
          },
        ]
      : []),
  ];
}

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

  const breaks = new Set<number>([0]);
  for (const prof of [raised.prof, flat.prof]) {
    let z = 0;
    for (const slab of prof) {
      z += slab.thicknessNm;
      breaks.add(Math.round(z * 1e6) / 1e6);
    }
  }
  const zs = [...breaks].sort((a, b) => a - b);

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
  stack(flat.prof, { x0: 0, x1: px, y0: 0, y1: y0 });
  stack(flat.prof, { x0: 0, x1: px, y0: y1, y1: py });
  stack(flat.prof, { x0: 0, x1: x0, y0, y1 });
  stack(flat.prof, { x0: x1, x1: px, y0, y1 });
  stack(raised.prof, { x0, x1, y0, y1 });
  return solids;
}
