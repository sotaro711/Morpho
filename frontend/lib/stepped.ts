/**
 * 段付き周期構造のモデル。
 *
 * 「全ブロック（カラム）は同じ層スタックを共有し、基板上げの有無だけが異なる」
 * という組み立て規約をこのモジュールに閉じ込める（stack.ts の段付き版）。
 * ブロックが空なら平面多層膜（従来どおり）で、モード切替は存在しない —
 * 設定の結果としてどちらかになる。
 *
 * バックエンド検証スクリプト backend/scripts/stepped_grating_validation.py の
 * build_sim() と同じ水平スライス法の TypeScript 移植:
 * 全カラムの層境界（基板上げとペア境界の互い違い）を集めて水平スライスに分割し、
 * 各スライスを「矩形領域の並び」として表す。
 *
 * React に依存しない純粋なモジュールなので "use client" は付けない。
 */

import type {
  EditableLayer,
  LayerDTO,
  SimulationRequest,
} from "@/lib/api/client";
import type { Medium, Settings } from "@/lib/stack";
import { toSimulationRequest } from "@/lib/stack";

/** 段差の 1 ブロック（カラム）。id は React のキー用。 */
export type StepBlock = { id: string; widthNm: number; raised: boolean };

/** 段差の設定。blocks が空 = 段差なし = 平面多層膜。 */
export type SteppedConfig = {
  raiseNm: number;
  blocks: StepBlock[];
  /** 最大回折次数 M（m = -M〜+M を計算に含める）。基底数は 2M+1。 */
  maxOrder: number;
};

/**
 * 最大回折次数の既定値（基底数 23）と UI で許す上限。
 * M=11 は参照構造(900/300 ブロック・TiO2/SiO2 7 ペア)で M=30 との差が
 * 全点 ≤0.03 に収まることを確認済み。計算量は基底数のほぼ 3 乗なので
 * M=30 比で約 18 倍速い。より細かいパターンで収束が怪しいときは UI で上げる。
 */
export const DEFAULT_MAX_ORDER = 11;
export const MAX_ORDER_LIMIT = 30;

export const DEFAULT_STEPPED: SteppedConfig = {
  raiseNm: 235, // 研究の設計値 λ0/2（λ0 = 470nm）
  blocks: [],
  maxOrder: DEFAULT_MAX_ORDER,
};

/** 段差が設定されているか（= 段付き周期構造として計算するか）。 */
export function isStepped(config: SteppedConfig): boolean {
  return config.blocks.some((b) => b.widthNm > 0);
}

/** 単位胞の周期（全ブロック幅の合計）。 */
export function periodNm(config: SteppedConfig): number {
  return config.blocks.reduce((sum, b) => sum + b.widthNm, 0);
}

// 入射媒質は空気に固定（stack.ts の規約と同じ。スライスの背景材料にも使う）。
const AIR: Medium = { name: "空気", n: 1.0, k: 0 };

/** 1 カラムを構成するスラブ（下 = 基板側 → 上 = 入射側の順）。 */
export type Slab = { name: string; thicknessNm: number; n: number; k: number };

function columnProfile(
  films: EditableLayer[],
  substrate: Medium,
  raised: boolean,
  raiseNm: number,
): Slab[] {
  const prof: Slab[] = [];
  if (raised) {
    // 基板上げ = 基板材料の台座。名前も基板と揃え、断面図で同じ色になるようにする
    prof.push({ name: substrate.name, thicknessNm: raiseNm, n: substrate.n, k: substrate.k });
  }
  // films は入射側（上）→ 基板側（下）の順なので、下から積むために反転する
  for (const l of [...films].reverse()) {
    prof.push({ name: l.name, thicknessNm: l.thicknessNm, n: l.n, k: l.k });
  }
  return prof;
}

/** プロファイル中の高さ z の材料。スタックの上（空気）なら null。 */
function materialAt(prof: Slab[], zNm: number): Slab | null {
  let z0 = 0;
  for (const slab of prof) {
    if (z0 <= zNm && zNm < z0 + slab.thicknessNm) return slab;
    z0 += slab.thicknessNm;
  }
  return null;
}

/**
 * 現在の入力から API リクエストを組み立てる。
 * 段差が無ければ平面版（toSimulationRequest）にそのまま委譲する。
 */
export function toSteppedSimulationRequest(
  settings: Settings,
  films: EditableLayer[],
  substrate: Medium,
  config: SteppedConfig,
): SimulationRequest {
  if (!isStepped(config)) {
    return toSimulationRequest(settings, films, substrate);
  }

  // カラム（x 方向の区間）と、その z プロファイル
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

  // 全カラムの層境界を集めて z 方向のスライスを作る（浮動小数の同値判定は丸めで）
  const breaks = new Set<number>([0]);
  for (const col of columns) {
    let z = 0;
    for (const slab of col.prof) {
      z += slab.thicknessNm;
      breaks.add(Math.round(z * 1e6) / 1e6);
    }
  }
  const zs = [...breaks].sort((a, b) => a - b);

  // 入射側（上）の半無限空気層 → スライスを上から順に → 基板の半無限層
  const layers: LayerDTO[] = [
    { name: AIR.name, thicknessNm: 0, n: AIR.n, k: AIR.k, regions: [] },
  ];
  for (let i = zs.length - 2; i >= 0; i--) {
    const zMid = (zs[i] + zs[i + 1]) / 2;
    const regions = columns.flatMap((col) => {
      const slab = materialAt(col.prof, zMid);
      return slab === null
        ? []
        : [{ xNm: col.xNm, widthNm: col.widthNm, n: slab.n, k: slab.k }];
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
    n: substrate.n,
    k: substrate.k,
    regions: [],
  });

  return {
    ...settings,
    // 基底数は最大回折次数から決まる（m = -M〜+M の 2M+1 本）
    numBasis: 2 * config.maxOrder + 1,
    periodNm: period,
    layers,
  };
}

/** 表示用: 1 カラム分の描画情報。slabs は下から順で、zNm はカラム内の下端高さ。 */
export type StructureColumn = {
  xNm: number;
  widthNm: number;
  raised: boolean;
  slabs: (Slab & { zNm: number })[];
};

/**
 * 断面図用のカラム分解。計算用スライサーと同じ columnProfile を源にするので、
 * 表示される構造と計算される構造は常に一致する。ブロックが空なら空配列。
 */
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
