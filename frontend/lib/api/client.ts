import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

// openapi-fetch クライアント。/api/* は next.config.ts の rewrites で
// FastAPI バックエンド (:8000) にプロキシされる。
export const apiClient = createClient<paths>({ baseUrl: "/" });

// 生成スキーマから使いやすい別名を切り出す（フロント側はこれを使う）。
export type SimulationRequest = components["schemas"]["SimulationRequest"];
export type SimulationResponse = components["schemas"]["SimulationResponse"];
export type LayerDTO = components["schemas"]["LayerDTO"];
export type Polarization = components["schemas"]["Polarization"];
export type SweepRequest = components["schemas"]["SweepRequest"];
export type SweepResponse = components["schemas"]["SweepResponse"];
export type SweepEntry = components["schemas"]["SweepEntryDTO"];

// エディタ内部用：React の安定キーのため id を持つ層。API 送信時に id を外す。
export type EditableLayer = LayerDTO & { id: string };

/** API エラーから detail を取り出して Error にする。 */
function toError(error: unknown): Error {
  const detail =
    typeof error === "object" && error !== null && "detail" in error
      ? JSON.stringify((error as { detail: unknown }).detail)
      : String(error);
  return new Error(detail);
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
