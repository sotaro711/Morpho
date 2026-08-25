"use client";

import { Trash2 } from "lucide-react";
import { useState } from "react";

import { NumberInput } from "@/components/NumberInput";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { EditableLayer } from "@/lib/api/client";

// ペア挿入フォームの1層分（名前・厚さ・n・k）。
type PairLayer = { name: string; thicknessNm: number; n: number; k: number };

type Props = {
  layers: EditableLayer[];
  onChange: (layers: EditableLayer[]) => void;
};

export function LayerEditor({ layers, onChange }: Props) {
  // ペア挿入フォームのローカル状態。
  const [pairA, setPairA] = useState<PairLayer>({ name: "A", thicknessNm: 100, n: 2.5, k: 0 });
  const [pairB, setPairB] = useState<PairLayer>({ name: "B", thicknessNm: 100, n: 1.5, k: 0 });
  const [pairCount, setPairCount] = useState(5);

  const update = (i: number, patch: Partial<EditableLayer>) =>
    onChange(layers.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));

  const addLayer = () => {
    // 積み上げ：新しい層をスタックの一番上（入射側寄り＝先頭）に追加する。
    const inserted: EditableLayer = {
      id: crypto.randomUUID(),
      name: `film${layers.length + 1}`,
      thicknessNm: 100,
      n: 1.5,
      k: 0,
    };
    onChange([inserted, ...layers]);
  };

  const removeLayer = (i: number) =>
    onChange(layers.filter((_, idx) => idx !== i));

  const insertPairs = () => {
    const n = Math.max(1, Math.floor(pairCount));
    const block: EditableLayer[] = [];
    for (let p = 0; p < n; p++) {
      // [A, B] の順（A が入射側寄り）。スタックの一番上にまとめて積む。
      block.push({ id: crypto.randomUUID(), ...pairA });
      block.push({ id: crypto.randomUUID(), ...pairB });
    }
    onChange([...block, ...layers]);
  };

  // 番号は基板側から数える（基板に接する膜が第1層、積み上げるほど大きい）。
  // films は入射側→基板の順なので、末尾が第1層。
  const roleOf = (i: number) => `第${layers.length - i}層`;

  return (
    <div className="grid gap-3">
      <div className="grid max-h-[55vh] gap-3 overflow-y-auto pr-1">
        {layers.length === 0 && (
          <p className="text-xs text-muted-foreground">
            多層膜なし（入射媒質と基板の界面のみ）。下から層を追加できます。
          </p>
        )}
        {layers.map((layer, i) => (
          <div key={layer.id} className="rounded-lg border p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-semibold">{roleOf(i)}</span>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={`${roleOf(i)}を削除`}
              onClick={() => removeLayer(i)}
              className="h-7 w-7 text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <Field label="名前">
              <Input
                value={layer.name}
                onChange={(e) => update(i, { name: e.target.value })}
              />
            </Field>
            <Field label="厚さ (nm)">
              <NumberInput
                value={layer.thicknessNm}
                onChange={(v) => update(i, { thicknessNm: v })}
              />
            </Field>
            <Field label="屈折率 n">
              <NumberInput
                step={0.01}
                value={layer.n}
                onChange={(v) => update(i, { n: v })}
              />
            </Field>
            <Field label="消衰係数 k">
              <NumberInput
                step={0.01}
                value={layer.k}
                onChange={(v) => update(i, { k: v })}
              />
            </Field>
          </div>
        </div>
        ))}
      </div>

      <Button type="button" variant="outline" onClick={addLayer}>
        + 層を追加
      </Button>

      {/* ペアをまとめて挿入（A,B を N 組、入射側直下に積み上げる） */}
      <div className="rounded-lg border border-dashed p-3">
        <p className="mb-2 text-sm font-semibold">ペアをまとめて挿入</p>
        <PairRow label="層 A（上）" value={pairA} onChange={setPairA} />
        <div className="mt-2">
          <PairRow label="層 B（下）" value={pairB} onChange={setPairB} />
        </div>
        <div className="mt-3 flex items-end gap-2">
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
    </div>
  );
}

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
    <div className="grid grid-cols-[auto_1fr_1fr_1fr_1fr] items-end gap-2">
      <span className="pb-2 text-xs text-muted-foreground">{label}</span>
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
      <Field label="屈折率 n">
        <NumberInput
          step={0.01}
          value={value.n}
          onChange={(v) => onChange({ ...value, n: v })}
        />
      </Field>
      <Field label="消衰係数 k">
        <NumberInput
          step={0.01}
          value={value.k}
          onChange={(v) => onChange({ ...value, k: v })}
        />
      </Field>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-1">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}
