import type {
  EditableLayer,
  LayerDTO,
  SimulationRequest,
} from "@/lib/api/client";

export type Settings = Omit<SimulationRequest, "layers" | "thetaDeg">;

export type Optics = {
  n: number;
  k: number;
  materialId?: string | null;
  nameBeforeMaterial?: string;
};

export type Medium = { name: string } & Optics;

export function apiOptics({ n, k, materialId }: Optics): Pick<LayerDTO, "n" | "k" | "materialId"> {
  return materialId ? { materialId, k: 0 } : { n, k };
}

export const DEFAULT_SETTINGS: Settings = {
  wlMin: 380,
  wlMax: 780,
  wlPoints: 81,
  pol: "s",
  phiDeg: 0,
  numBasis: 1,
};

export const DEFAULT_FILMS: EditableLayer[] = [];

export const DEFAULT_SUBSTRATE: Medium = { name: "樹脂", n: 1.5, k: 0 };

const INCIDENT_AIR: Medium = { name: "空気", n: 1.0, k: 0 };

export function structureLayers(
  films: EditableLayer[],
  substrate: Medium,
): LayerDTO[] {
  return [
    ...films.map((l) => ({
      name: l.name,
      thicknessNm: l.thicknessNm,
      n: l.n,
      k: l.k,
      materialId: l.materialId,
      regions: l.regions,
    })),
    {
      name: substrate.name,
      thicknessNm: 0,
      n: substrate.n,
      k: substrate.k,
      materialId: substrate.materialId,
      regions: [],
    },
  ];
}

function buildLayers(films: EditableLayer[], substrate: Medium): LayerDTO[] {
  return [
    { name: INCIDENT_AIR.name, thicknessNm: 0, n: INCIDENT_AIR.n, k: INCIDENT_AIR.k, regions: [] },
    ...films.map((l) => ({
      name: l.name,
      thicknessNm: l.thicknessNm,
      ...apiOptics(l),
      regions: l.regions,
    })),
    { name: substrate.name, thicknessNm: 0, ...apiOptics(substrate), regions: [] },
  ];
}

export function toSimulationRequest(
  settings: Settings,
  films: EditableLayer[],
  substrate: Medium,
): SimulationRequest {
  return { ...settings, thetaDeg: 0, layers: buildLayers(films, substrate) };
}
