/**
 * 層スタックのモデル。
 *
 * 「入射側には必ず空気を置く」「基板は末尾に厚さ 0（半無限）で置く」といった
 * 構造の組み立て規約はこのモジュールに閉じ込める。バックエンドの
 * domain/entities と対になる知識で、View が持つべきものではない。
 *
 * React に依存しない純粋なモジュールなので "use client" は付けない。
 */

import type {
  EditableLayer,
  LayerDTO,
  SimulationRequest,
} from "@/lib/api/client";

/**
 * 計算条件のスカラー部分（層・媒質を除く）。
 * 入射角は角度スイープ（thetaDegs）で指定するため UI からは除外する。
 */
export type Settings = Omit<SimulationRequest, "layers" | "thetaDeg">;

/**
 * 層や基板の光学定数。materialId があれば登録した材料（波長分散）を使い、n, k は使わない。
 * n, k は手入力の値で、材料を選んでいる間も残しておき、手入力に戻したときに復元する。
 */
export type Optics = {
  n: number;
  k: number;
  materialId?: string | null;
  /** 材料を選ぶ前の層名。材料を外したときに名前を戻すためだけに使う（API には送らない）。 */
  nameBeforeMaterial?: string;
};

/** 入射媒質・基板（半無限）の名前と光学定数。 */
export type Medium = { name: string } & Optics;

/**
 * API に送る光学定数。材料を選んでいれば materialId、なければ n, k。
 * k はスキーマ上必須（既定値 0）なので、材料のときは 0 を添える（API は materialId を優先する）。
 */
export function apiOptics({ n, k, materialId }: Optics): Pick<LayerDTO, "n" | "k" | "materialId"> {
  return materialId ? { materialId, k: 0 } : { n, k };
}

export const DEFAULT_SETTINGS: Settings = {
  wlMin: 380,
  wlMax: 780,
  wlPoints: 81,
  pol: "s",
  numBasis: 1, // 平面多層膜は 0 次のみで厳密（周期構造対応時に増やす）
};

/** 既定の多層膜（films）。id は固定（SSR/ハイドレーションのズレ回避）。 */
export const DEFAULT_FILMS: EditableLayer[] = [
  {
    id: "default-film",
    name: "film",
    thicknessNm: 150,
    n: 2.5,
    k: 0,
    regions: [],
  },
];

export const DEFAULT_SUBSTRATE: Medium = { name: "SUS", n: 1.71, k: 2.88 };

// 入射媒質は空気に固定（光が入ってくる側。UI には出さない）。
const INCIDENT_AIR: Medium = { name: "空気", n: 1.0, k: 0 };

/** 多層膜 + 基板（断面図に表示する層。入射側の空気は含まない）。 */
export function structureLayers(
  films: EditableLayer[],
  substrate: Medium,
): LayerDTO[] {
  return [
    // EditableLayer からエディタ内部用の id を落として LayerDTO にする。
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

// API 用の層リスト（入射側→基板）。先頭に入射側の空気を付与する。
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

/** 現在の入力から API リクエストを組み立てる。 */
export function toSimulationRequest(
  settings: Settings,
  films: EditableLayer[],
  substrate: Medium,
): SimulationRequest {
  // thetaDeg はスキーマ上必須だが、sweep API は thetaDegs のみ参照するため 0 固定
  return { ...settings, thetaDeg: 0, layers: buildLayers(films, substrate) };
}
