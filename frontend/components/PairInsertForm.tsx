"use client";

import { useState } from "react";

import { Field } from "@/components/Field";
import { NumberInput } from "@/components/NumberInput";
import { OpticsFields } from "@/components/OpticsFields";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { EditableLayer } from "@/lib/api/client";
import type { Optics } from "@/lib/stack";

// ペア挿入フォームの1層分（名前・厚さ・光学定数）。
type PairLayer = { name: string; thicknessNm: number } & Optics;

type Props = {
  onInsert: (block: EditableLayer[]) => void;
};

/** A/B 層のペアを N 組まとめて作って渡すフォーム。 */
export function PairInsertForm({ onInsert }: Props) {
  const [pairA, setPairA] = useState<PairLayer>({ name: "A", thicknessNm: 100, n: 2.5, k: 0 });
  const [pairB, setPairB] = useState<PairLayer>({ name: "B", thicknessNm: 100, n: 1.5, k: 0 });
  const [pairCount, setPairCount] = useState(5);

  const insertPairs = () => {
    const n = Math.max(1, Math.floor(pairCount));
    const block: EditableLayer[] = [];
    for (let p = 0; p < n; p++) {
      // [A, B] の順（A が入射側寄り）。
      block.push({ id: crypto.randomUUID(), ...pairA, regions: [] });
      block.push({ id: crypto.randomUUID(), ...pairB, regions: [] });
    }
    onInsert(block);
  };

  return (
    <div className="grid gap-2">
      <PairRow label="層 A（上）" value={pairA} onChange={setPairA} />
      <PairRow label="層 B（下）" value={pairB} onChange={setPairB} />
      <div className="mt-1 flex items-end gap-2">
        <div className="grid gap-1">
          <Label className="text-xs text-muted-foreground">ペア数</Label>
          <NumberInput
            min={1}
            value={pairCount}
            onChange={setPairCount}
            className="w-24"
          />
        </div>
        <Button type="button" onClick={insertPairs}>
          ペアを挿入
        </Button>
      </div>
    </div>
  );
}

/** 多層膜の層と同じ 2 段の形（名前・厚さ / n・k・材料）。 */
function PairRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: PairLayer;
  onChange: (v: PairLayer) => void;
}) {
  return (
    <div className="rounded-lg border p-3">
      <span className="mb-2 block text-sm font-semibold">{label}</span>
      <div className="grid grid-cols-2 gap-2">
        <Field label="名前">
          <Input
            value={value.name}
            onChange={(e) => onChange({ ...value, name: e.target.value })}
          />
        </Field>
        <Field label="厚さ (nm)">
          <NumberInput
            value={value.thicknessNm}
            onChange={(v) => onChange({ ...value, thicknessNm: v })}
          />
        </Field>
        <OpticsFields value={value} onChange={(patch) => onChange({ ...value, ...patch })} />
      </div>
    </div>
  );
}
