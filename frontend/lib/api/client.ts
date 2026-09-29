import createClient from "openapi-fetch";

import { authMiddleware } from "./auth-middleware";
import type { components, paths } from "./schema";

// openapi-fetch クライアント。/api/* は next.config.ts の rewrites で
// FastAPI バックエンド (:8000) にプロキシされる。
export const apiClient = createClient<paths>({ baseUrl: "/" });
apiClient.use(authMiddleware);

// 生成スキーマから使いやすい別名を切り出す（フロント側はこれを使う）。
export type SimulationRequest = components["schemas"]["SimulationRequest"];
export type SimulationResponse = components["schemas"]["SimulationResponse"];
export type LayerDTO = components["schemas"]["LayerDTO"];
export type Polarization = components["schemas"]["Polarization"];
export type SweepRequest = components["schemas"]["SweepRequest"];
export type SweepResponse = components["schemas"]["SweepResponse"];
export type SweepEntry = components["schemas"]["SweepEntryDTO"];
export type ColorDTO = components["schemas"]["ColorDTO"];
export type DiffractionModes = components["schemas"]["DiffractionModesDTO"];

// エディタ内部用：React の安定キーのため id を持つ層。API 送信時に id を外す。
// API では materialId 指定時に n, k を省略できるが、エディタは常に数値を持つ
// （材料を外したときに復元するため）。nameBeforeMaterial は stack.ts の Optics を参照。
export type EditableLayer = LayerDTO & {
  id: string;
  n: number;
  k: number;
  nameBeforeMaterial?: string;
};

/**
 * API エラーから detail を取り出して Error にする。
 * 文字列の detail はバックエンドが日本語の文言で返したものなので、そのまま表示する。
 * それ以外（Pydantic の検証エラーの配列など）は JSON にして見えるようにする。
 */
function toError(error: unknown): Error {
  if (typeof error !== "object" || error === null || !("detail" in error)) {
    return new Error(String(error));
  }
  const { detail } = error;
  return new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
}

/** シミュレーションを実行する。失敗時は detail を含む Error を投げる。 */
export async function simulate(
  body: SimulationRequest,
): Promise<SimulationResponse> {
  const { data, error } = await apiClient.POST("/api/simulate", { body });
  if (error) throw toError(error);
  return data;
}

/** 入射角スイープ(角度ごとのスペクトルと任意で色)を実行する。 */
export async function simulateSweep(body: SweepRequest): Promise<SweepResponse> {
  const { data, error } = await apiClient.POST("/api/simulate/sweep", { body });
  if (error) throw toError(error);
  return data;
}

export type MaterialSummary = components["schemas"]["MaterialSummaryDTO"];
export type MaterialDetail = components["schemas"]["MaterialDTO"];
export type DispersionPoint = components["schemas"]["DispersionPointDTO"];

/** ログイン中のユーザーが登録した材料の一覧（id と名前）。名前順。 */
export async function listMaterials(): Promise<MaterialSummary[]> {
  const { data, error } = await apiClient.GET("/api/materials");
  if (error) throw toError(error);
  return data;
}

/** 材料の詳細（n, k の表）。 */
export async function getMaterial(id: string): Promise<MaterialDetail> {
  const { data, error } = await apiClient.GET("/api/materials/{material_id}", {
    params: { path: { material_id: id } },
  });
  if (error) throw toError(error);
  return data;
}

/** 材料を登録する。content はファイルの中身（読み取りはバックエンドで行う）。 */
export async function createMaterial(name: string, content: string): Promise<MaterialDetail> {
  const { data, error } = await apiClient.POST("/api/materials", { body: { name, content } });
  if (error) throw toError(error);
  return data;
}

/** 材料の名前を変える。 */
export async function renameMaterial(id: string, name: string): Promise<MaterialSummary> {
  const { data, error } = await apiClient.PATCH("/api/materials/{material_id}", {
    params: { path: { material_id: id } },
    body: { name },
  });
  if (error) throw toError(error);
  return data;
}

/** 材料を削除する。 */
export async function deleteMaterial(id: string): Promise<void> {
  const { error } = await apiClient.DELETE("/api/materials/{material_id}", {
    params: { path: { material_id: id } },
  });
  if (error) throw toError(error);
}
