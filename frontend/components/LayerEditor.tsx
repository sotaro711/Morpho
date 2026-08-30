"use client";

import { Trash2 } from "lucide-react";

import { Field } from "@/components/Field";
import { NumberInput } from "@/components/NumberInput";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { EditableLayer } from "@/lib/api/client";

type Props = {
  layers: EditableLayer[];
  onChange: (layers: EditableLayer[]) => void;
};

export function LayerEditor({ layers, onChange }: Props) {
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
      regions: [],
    };
    onChange([inserted, ...layers]);
  };

  const removeLayer = (i: number) =>
    onChange(layers.filter((_, idx) => idx !== i));

  // 番号は基板側から数える（基板に接する膜が第1層、積み上げるほど大きい）。
  // films は入射側→基板の順なので、末尾が第1層。
  const roleOf = (i: number) => `第${layers.length - i}層`;

  return (
    <div className="grid gap-3">
      <div className="flex gap-2">
        <Button type="button" variant="outline" onClick={addLayer} className="flex-1">
          + 層を追加
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={layers.length === 0}
          onClick={() => onChange([])}
          className="text-muted-foreground hover:text-destructive"
        >
          <Trash2 className="h-4 w-4 text-destructive/70" />
          全て削除
        </Button>
      </div>

      <div className="grid max-h-[55vh] gap-3 overflow-y-auto pr-1">
        {layers.length === 0 && (
          <p className="text-xs text-muted-foreground">
            多層膜なし（入射媒質と基板の界面のみ）。上のボタンから層を追加できます。
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
    </div>
  );
}
