"use client";

import { Button } from "@/components/ui/button";

/** 選択肢を横に並べたボタンから 1 つを選ぶ切替。 */
export function SegmentedToggle<T extends string | number>({
  label,
  options,
  value,
  onChange,
}: {
  /** 読み上げ用の名前。 */
  label: string;
  options: readonly { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-1">
      {options.map((o) => (
        <Button
          key={o.value}
          role="radio"
          aria-checked={value === o.value}
          size="sm"
          variant={value === o.value ? "default" : "outline"}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </Button>
      ))}
    </div>
  );
}
