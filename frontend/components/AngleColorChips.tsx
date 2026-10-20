import type { SweepResponse } from "@/lib/api/client";
import { entryColor, type DiffractionMode } from "@/lib/diffraction";

/** 入射角ごとの見た目の色チップ(研究スライド上段の形式)。 */
export function AngleColorChips({
  sweep,
  mode,
}: {
  sweep: SweepResponse;
  mode: DiffractionMode;
}) {
  return (
    <div className="flex justify-center gap-8">
      {sweep.entries.map((e) => {
        const color = entryColor(e, mode);
        return (
          <div key={e.thetaDeg} className="grid justify-items-center gap-1.5">
            <span className="text-sm font-semibold">{Math.round(e.thetaDeg)}°</span>
            <div
              className="h-16 w-16 rounded-md border"
              style={{ backgroundColor: color?.hex }}
            />
            <span className="text-xs text-muted-foreground">{color?.hex}</span>
          </div>
        );
      })}
    </div>
  );
}
