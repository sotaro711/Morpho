import type { ColorDTO, SweepEntry, SweepResponse } from "@/lib/api/client";

export type DiffractionMode = "zeroth" | "nonZeroth" | "total";

export const DEFAULT_DIFFRACTION_MODE: DiffractionMode = "total";

export const DIFFRACTION_MODES: {
  value: DiffractionMode;
  label: string;
  description: string;
}[] = [
  { value: "zeroth", label: "0次のみ（正反射）", description: "入射角と同じ角度に返る光。鏡の向きで見た色" },
  { value: "nonZeroth", label: "0次以外（回折光）", description: "正反射以外の方向へ散った高次回折光の合計" },
  { value: "total", label: "全次数", description: "反射側に戻った光の合計。0次 + 0次以外" },
];

export function hasDiffractionModes(sweep: SweepResponse | null): boolean {
  return sweep?.entries.some((e) => e.diffraction != null) ?? false;
}

export function entryReflectance(entry: SweepEntry, mode: DiffractionMode): number[] {
  if (mode === "zeroth" || !entry.diffraction) return entry.R;
  return entry.diffraction[mode].R;
}

export function entryColor(
  entry: SweepEntry,
  mode: DiffractionMode,
): ColorDTO | null | undefined {
  if (mode === "zeroth" || !entry.diffraction) return entry.color;
  return entry.diffraction[mode].color;
}

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
