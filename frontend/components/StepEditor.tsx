"use client";

import { NumberInput } from "@/components/NumberInput";
import { Label } from "@/components/ui/label";
import type { StepBlock, SteppedConfig } from "@/lib/stepped";

type Props = {
  value: SteppedConfig;
  onChange: (v: SteppedConfig) => void;
};

/**
 * 段差(基板上げ)のビジュアルエディタ。
 *
 * ブロックを断面図そのままの「箱」として横に並べる。箱の幅は実際の幅に比例し、
 * 「上げ」の箱は上にずれて表示される — 見たままが計算される構造になる。
 * 箱をクリックすると上げ/平が切り替わり、ホバーで削除ボタンが出る。
 * ブロックが空の間は平面多層膜として計算される。
 */
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
        // 交互に「上げ」を初期値にする(段付き構造の典型形に寄せる)
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
      <div className="flex items-center gap-2">
        <Label className="text-xs text-muted-foreground">上げ高さ (nm)</Label>
        <NumberInput
          step={1}
          value={value.raiseNm}
          onChange={(raiseNm) => patch({ raiseNm })}
          className="w-24"
        />
      </div>

      <div className="flex items-end gap-1.5 rounded-lg border bg-muted/30 px-3 pb-3 pt-9">
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
              className="absolute -right-1.5 -top-7 hidden h-5 w-5 items-center justify-center rounded-full border bg-background text-xs leading-none text-muted-foreground shadow-sm group-hover:flex"
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

      {value.blocks.length === 0 && (
        <p className="text-xs text-muted-foreground">
          ＋でブロックを並べると段付き周期構造になります（空のままなら平面多層膜）。
        </p>
      )}
    </div>
  );
}
