"use client";

import { Button } from "@/components/ui/button";
import { DIFFRACTION_MODES, type DiffractionMode } from "@/lib/diffraction";

/**
 * 表示する回折次数の見方（0次のみ / 0次以外 / 全次数）の切替。
 * 再計算は不要で、受け取り済みの結果のどの系列を描くかだけを切り替える。
 */
export function DiffractionModeToggle({
  value,
  onChange,
}: {
  value: DiffractionMode;
  onChange: (v: DiffractionMode) => void;
}) {
  return (
    <div className="grid gap-1.5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">表示する回折次数</span>
        <div role="radiogroup" className="flex flex-wrap gap-1">
          {DIFFRACTION_MODES.map((m) => (
            <Button
              key={m.value}
              role="radio"
              aria-checked={value === m.value}
              size="sm"
              variant={value === m.value ? "default" : "outline"}
              title={m.description}
              onClick={() => onChange(m.value)}
            >
              {m.label}
            </Button>
          ))}
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        0次以外の回折光は段差のある周期構造でのみ現れます。平面多層膜では「0次以外」は 0、「全次数」は「0次のみ」と一致します。
      </p>
    </div>
  );
}
