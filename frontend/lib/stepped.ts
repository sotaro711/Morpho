import type {
  EditableLayer,
  LayerDTO,
  SimulationRequest,
} from "@/lib/api/client";
import type { Medium, Optics, Settings } from "@/lib/stack";
import { apiOptics, toSimulationRequest } from "@/lib/stack";

export type StepBlock = { id: string; widthNm: number; raised: boolean };

export type SteppedConfig = {
  raiseNm: number;
  blocks: StepBlock[];
  maxOrder: number;
};

export const DEFAULT_MAX_ORDER = 11;
export const MAX_ORDER_LIMIT = 30;

export const DEFAULT_STEPPED: SteppedConfig = {
  raiseNm: 235,
  blocks: [],
  maxOrder: DEFAULT_MAX_ORDER,
};

export function isStepped(config: SteppedConfig): boolean {
  return config.blocks.some((b) => b.widthNm > 0);
}

export function periodNm(config: SteppedConfig): number {
  return config.blocks.reduce((sum, b) => sum + b.widthNm, 0);
}

const AIR: Medium = { name: "空気", n: 1.0, k: 0 };

export type Slab = { name: string; thicknessNm: number } & Optics;

export function columnProfile(
  films: EditableLayer[],
  substrate: Medium,
  raised: boolean,
  raiseNm: number,
): Slab[] {
  const prof: Slab[] = [];
  if (raised) {
    prof.push({ ...substrate, thicknessNm: raiseNm });
  }
  for (const l of [...films].reverse()) {
    prof.push({
      name: l.name,
      thicknessNm: l.thicknessNm,
      n: l.n,
      k: l.k,
      materialId: l.materialId,
    });
  }
  return prof;
}

export function materialAt(prof: Slab[], zNm: number): Slab | null {
  let z0 = 0;
  for (const slab of prof) {
    if (z0 <= zNm && zNm < z0 + slab.thicknessNm) return slab;
    z0 += slab.thicknessNm;
  }
  return null;
}

export function toSteppedSimulationRequest(
  settings: Settings,
  films: EditableLayer[],
  substrate: Medium,
  config: SteppedConfig,
): SimulationRequest {
  if (!isStepped(config)) {
    return toSimulationRequest(settings, films, substrate);
  }

  const blocks = config.blocks.filter((b) => b.widthNm > 0);
  const columns: { xNm: number; widthNm: number; prof: Slab[] }[] = [];
  let x = 0;
  for (const b of blocks) {
    columns.push({
      xNm: x,
      widthNm: b.widthNm,
      prof: columnProfile(films, substrate, b.raised, config.raiseNm),
    });
    x += b.widthNm;
  }
  const period = x;

  const breaks = new Set<number>([0]);
  for (const col of columns) {
    let z = 0;
    for (const slab of col.prof) {
      z += slab.thicknessNm;
      breaks.add(Math.round(z * 1e6) / 1e6);
    }
  }
  const zs = [...breaks].sort((a, b) => a - b);

  const layers: LayerDTO[] = [
    { name: AIR.name, thicknessNm: 0, n: AIR.n, k: AIR.k, regions: [] },
  ];
  for (let i = zs.length - 2; i >= 0; i--) {
    const zMid = (zs[i] + zs[i + 1]) / 2;
    const regions = columns.flatMap((col) => {
      const slab = materialAt(col.prof, zMid);
      return slab === null
        ? []
        : [
            {
              shape: "stripe" as const,
              xNm: col.xNm,
              widthNm: col.widthNm,
              ...apiOptics(slab),
            },
          ];
    });
    layers.push({
      name: `slice${i}`,
      thicknessNm: zs[i + 1] - zs[i],
      n: AIR.n,
      k: AIR.k,
      regions,
    });
  }
  layers.push({
    name: substrate.name,
    thicknessNm: 0,
    ...apiOptics(substrate),
    regions: [],
  });

  return {
    ...settings,
    thetaDeg: 0,
    numBasis: 2 * config.maxOrder + 1,
    periodNm: period,
    layers,
  };
}

export type StructureColumn = {
  xNm: number;
  widthNm: number;
  raised: boolean;
  slabs: (Slab & { zNm: number })[];
};

export function structureColumns(
  films: EditableLayer[],
  substrate: Medium,
  config: SteppedConfig,
): { periodNm: number; columns: StructureColumn[] } {
  const blocks = config.blocks.filter((b) => b.widthNm > 0);
  const columns: StructureColumn[] = [];
  let x = 0;
  for (const b of blocks) {
    let z = 0;
    const slabs = columnProfile(films, substrate, b.raised, config.raiseNm).map(
      (slab) => {
        const placed = { ...slab, zNm: z };
        z += slab.thicknessNm;
        return placed;
      },
    );
    columns.push({ xNm: x, widthNm: b.widthNm, raised: b.raised, slabs });
    x += b.widthNm;
  }
  return { periodNm: x, columns };
}
