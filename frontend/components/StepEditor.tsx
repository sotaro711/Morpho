"use client";

import { Trash2 } from "lucide-react";

import { NumberInput } from "@/components/NumberInput";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { MAX_ORDER_LIMIT, type StepBlock, type SteppedConfig } from "@/lib/stepped";

type Props = {
  value: SteppedConfig;
  onChange: (v: SteppedConfig) => void;
};

export function StepEditor({ value, onChange }: Props) {
  const patch = (p: Partial<SteppedConfig>) => onChange({ ...value, ...p });

  const updateBlock = (i: number, p: Partial<StepBlock>) =>
    patch({
      blocks: value.blocks.map((b, idx) => (idx === i ? { ...b, ...p } : b)),
    });

  const addBlock = () =>
    patch({
      blocks: [
        ...value.blocks,
        {
          id: crypto.randomUUID(),
          widthNm: 300,
          raised: value.blocks.length % 2 === 1,
        },
      ],
    });

  const removeBlock = (i: number) =>
    patch({ blocks: value.blocks.filter((_, idx) => idx !== i) });

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <div className="flex items-center gap-2">
          <Label className="text-xs text-muted-foreground">上げ高さ (nm)</Label>
          <NumberInput
            step={1}
            value={value.raiseNm}
            onChange={(raiseNm) => patch({ raiseNm })}
            className="w-24"
          />
        </div>
        {value.blocks.length > 0 && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => patch({ blocks: [] })}
            className="order-last ml-auto text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="h-4 w-4 text-destructive/70" />
            全て削除
          </Button>
        )}
        {value.blocks.length > 0 && (
          <div
            className="flex items-center gap-2"
            title={`計算に含める回折次数の範囲 (±M、最大 ±${MAX_ORDER_LIMIT})。上げると精度が上がるが、計算時間は基底数 2M+1 のほぼ 3 乗で増える`}
          >
            <Label className="text-xs text-muted-foreground">回折次数 ±</Label>
            <NumberInput
              step={1}
              min={1}
              max={MAX_ORDER_LIMIT}
              value={value.maxOrder}
              onChange={(v) =>
                patch({
                  maxOrder: Math.min(MAX_ORDER_LIMIT, Math.max(1, Math.round(v))),
                })
              }
              className="w-20"
            />
          </div>
        )}
      </div>

      <div className="flex items-end gap-1.5 overflow-x-auto rounded-lg border bg-muted/30 px-3 pb-3 pt-9">
        {value.blocks.map((b, i) => (
          <div
            key={b.id}
            className="group relative grid min-w-[4.5rem] gap-1"
            style={{ flexGrow: b.widthNm, flexBasis: 0 }}
          >
            <button
              type="button"
              onClick={() => updateBlock(i, { raised: !b.raised })}
              title={b.raised ? "クリックで平らに" : "クリックで上げる"}
              aria-label={`ブロック${i + 1}(${b.raised ? "上げ" : "平"})`}
              className={`h-14 w-full rounded-sm border-2 transition-transform ${
                b.raised
                  ? "-translate-y-5 border-primary/70 bg-primary/25"
                  : "border-border bg-secondary"
              }`}
            />
            <button
              type="button"
              onClick={() => removeBlock(i)}
              aria-label={`ブロック${i + 1}を削除`}
              className={`absolute -right-1.5 z-10 hidden h-5 w-5 items-center justify-center rounded-full border bg-background text-xs leading-none text-muted-foreground shadow-sm group-hover:flex ${
                b.raised ? "-top-7" : "-top-2"
              }`}
            >
              ×
            </button>
            <NumberInput
              step={10}
              min={1}
              value={b.widthNm}
              onChange={(widthNm) => updateBlock(i, { widthNm })}
              className="h-7 px-1 text-center text-xs"
            />
          </div>
        ))}
        <button
          type="button"
          onClick={addBlock}
          aria-label="ブロックを追加"
          className="mb-8 h-14 w-12 shrink-0 rounded-sm border border-dashed text-lg text-muted-foreground hover:bg-secondary"
        >
          ＋
        </button>
      </div>
    </div>
  );
}
