import createClient from "openapi-fetch";

import { authMiddleware } from "./auth-middleware";
import type { components, paths } from "./schema";

export const apiClient = createClient<paths>({ baseUrl: "/" });
apiClient.use(authMiddleware);

export type SimulationRequest = components["schemas"]["SimulationRequest"];
export type SimulationResponse = components["schemas"]["SimulationResponse"];
export type LayerDTO = components["schemas"]["LayerDTO"];
export type Polarization = components["schemas"]["Polarization"];
export type SweepRequest = components["schemas"]["SweepRequest"];
export type SweepResponse = components["schemas"]["SweepResponse"];
export type SweepEntry = components["schemas"]["SweepEntryDTO"];
export type ColorDTO = components["schemas"]["ColorDTO"];
export type DiffractionModes = components["schemas"]["DiffractionModesDTO"];

export type EditableLayer = LayerDTO & {
  id: string;
  n: number;
  k: number;
  nameBeforeMaterial?: string;
};

function toError(error: unknown): Error {
  if (typeof error !== "object" || error === null || !("detail" in error)) {
    return new Error(String(error));
  }
  const { detail } = error;
  return new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
}

export async function simulate(
  body: SimulationRequest,
): Promise<SimulationResponse> {
  const { data, error } = await apiClient.POST("/api/simulate", { body });
  if (error) throw toError(error);
  return data;
}

export async function simulateSweep(body: SweepRequest): Promise<SweepResponse> {
  const { data, error } = await apiClient.POST("/api/simulate/sweep", { body });
  if (error) throw toError(error);
  return data;
}

export type MaterialSummary = components["schemas"]["MaterialSummaryDTO"];
export type MaterialDetail = components["schemas"]["MaterialDTO"];
export type DispersionPoint = components["schemas"]["DispersionPointDTO"];

export async function listMaterials(): Promise<MaterialSummary[]> {
  const { data, error } = await apiClient.GET("/api/materials");
  if (error) throw toError(error);
  return data;
}

export async function getMaterial(id: string): Promise<MaterialDetail> {
  const { data, error } = await apiClient.GET("/api/materials/{material_id}", {
    params: { path: { material_id: id } },
  });
  if (error) throw toError(error);
  return data;
}

export async function createMaterial(name: string, content: string): Promise<MaterialDetail> {
  const { data, error } = await apiClient.POST("/api/materials", { body: { name, content } });
  if (error) throw toError(error);
  return data;
}

export async function renameMaterial(id: string, name: string): Promise<MaterialSummary> {
  const { data, error } = await apiClient.PATCH("/api/materials/{material_id}", {
    params: { path: { material_id: id } },
    body: { name },
  });
  if (error) throw toError(error);
  return data;
}

export async function deleteMaterial(id: string): Promise<void> {
  const { error } = await apiClient.DELETE("/api/materials/{material_id}", {
    params: { path: { material_id: id } },
  });
  if (error) throw toError(error);
}

export type ResultSummary = components["schemas"]["ResultSummaryDTO"];
export type ResultDetail = components["schemas"]["ResultDTO"];
export type ResultCreate = components["schemas"]["ResultCreateRequest"];

export async function listResults(): Promise<ResultSummary[]> {
  const { data, error } = await apiClient.GET("/api/results");
  if (error) throw toError(error);
  return data;
}

export async function getResult(id: string): Promise<ResultDetail> {
  const { data, error } = await apiClient.GET("/api/results/{result_id}", {
    params: { path: { result_id: id } },
  });
  if (error) throw toError(error);
  return data;
}

export async function saveResult(body: ResultCreate): Promise<ResultSummary> {
  const { data, error } = await apiClient.POST("/api/results", { body });
  if (error) throw toError(error);
  return data;
}

export async function deleteResult(id: string): Promise<void> {
  const { error } = await apiClient.DELETE("/api/results/{result_id}", {
    params: { path: { result_id: id } },
  });
  if (error) throw toError(error);
}
