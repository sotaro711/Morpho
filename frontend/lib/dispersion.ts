import type { DispersionPoint } from "@/lib/api/client";
import { DEFAULT_SETTINGS } from "@/lib/stack";

export const WL_MIN = DEFAULT_SETTINGS.wlMin;
export const WL_MAX = DEFAULT_SETTINGS.wlMax;

function interpolate(a: DispersionPoint, b: DispersionPoint, wl: number): DispersionPoint {
  const t = (wl - a.wavelengthNm) / (b.wavelengthNm - a.wavelengthNm);
  return { wavelengthNm: wl, n: a.n + (b.n - a.n) * t, k: a.k + (b.k - a.k) * t };
}

export function clipToRange(points: DispersionPoint[]): DispersionPoint[] {
  const clipped: DispersionPoint[] = [];
  points.forEach((p, i) => {
    const prev = points[i - 1];
    if (prev) {
      for (const edge of [WL_MIN, WL_MAX]) {
        if (prev.wavelengthNm < edge && edge < p.wavelengthNm) clipped.push(interpolate(prev, p, edge));
      }
    }
    if (WL_MIN <= p.wavelengthNm && p.wavelengthNm <= WL_MAX) clipped.push(p);
  });
  return clipped;
}

export function hasAbsorption(points: DispersionPoint[]): boolean {
  return clipToRange(points).some((p) => p.k > 0);
}
