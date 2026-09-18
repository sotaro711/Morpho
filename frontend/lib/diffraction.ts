import type { ColorDTO, SweepEntry, SweepResponse } from "@/lib/api/client";

/**
 * 反射光を回折次数で分けたときの見方。
 *
 * - zeroth:    0 次（正反射方向）だけ。従来どおりの R
 * - nonZeroth: 0 次以外（m ≠ 0）の合計。正反射以外の方向へ散った回折光
 * - total:     全次数の合計。反射側に戻った総エネルギー
 *
 * 別方向へ出る光の足し算なので R(total) = R(zeroth) + R(nonZeroth) が成り立つ。
 * 平面多層膜には 0 次以外が存在しないので nonZeroth は 0、total は zeroth と一致する。
 * バックエンドが diffraction を返さない場合はどれを選んでも 0 次を表示する。
 */
export type DiffractionMode = "zeroth" | "nonZeroth" | "total";

export const DIFFRACTION_MODES: {
  value: DiffractionMode;
  label: string;
  description: string;
}[] = [
  { value: "zeroth", label: "0次のみ（正反射）", description: "入射角と同じ角度に返る光。鏡の向きで見た色" },
  { value: "nonZeroth", label: "0次以外（回折光）", description: "正反射以外の方向へ散った高次回折光の合計" },
  { value: "total", label: "全次数", description: "反射側に戻った光の合計。0次 + 0次以外" },
];

/** スイープ結果が次数別の内訳を持つか。 */
export function hasDiffractionModes(sweep: SweepResponse | null): boolean {
  return sweep?.entries.some((e) => e.diffraction != null) ?? false;
}

/** 1 入射角分の、指定した見方での反射率スペクトル。内訳が無ければ 0 次にフォールバック。 */
export function entryReflectance(entry: SweepEntry, mode: DiffractionMode): number[] {
  if (mode === "zeroth" || !entry.diffraction) return entry.R;
  return entry.diffraction[mode].R;
}

/** 1 入射角分の、指定した見方での反射色。内訳が無ければ 0 次の色にフォールバック。 */
export function entryColor(
  entry: SweepEntry,
  mode: DiffractionMode,
): ColorDTO | null | undefined {
  if (mode === "zeroth" || !entry.diffraction) return entry.color;
  return entry.diffraction[mode].color;
}

/** チャートの縦軸ラベル。 */
export function reflectanceAxisLabel(mode: DiffractionMode): string {
  switch (mode) {
    case "nonZeroth":
      return "反射率 R（0次以外）";
    case "total":
      return "反射率 R（全次数）";
    default:
      return "反射率 R（0次）";
  }
}
