"use client";

import { NumberInput } from "@/components/NumberInput";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import type { StepBlock, SteppedConfig } from "@/lib/stepped";

type Props = {
  value: SteppedConfig;
  onChange: (v: SteppedConfig) => void;
};

/**
 * 段差（基板上げ）のエディタ。
 *
 * ブロック（カラム）の幅と「上げる/上げない」を行として並べる。
 * ブロックが空の間は平面多層膜として計算される（モード切替は存在しない）。
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
        // 交互に「上げ」を初期値にする（段付き構造の典型形に寄せる）
        {
          id: crypto.randomUUID(),
          widthNm: 300,
          raised: value.blocks.length % 2 === 0 ? false : true,
        },
      ],
    });

  const removeBlock = (i: number) =>
    patch({ blocks: value.blocks.filter((_, idx) => idx !== i) });

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-[1fr_2fr] items-end gap-2">
        <div className="grid gap-1">
          <Label className="text-xs text-muted-foreground">
            基板上げ高さ (nm)
          </Label>
          <NumberInput
            step={1}
            value={value.raiseNm}
            onChange={(raiseNm) => patch({ raiseNm })}
          />
        </div>
        <p className="pb-2 text-xs text-muted-foreground">
          λ₀/2（干渉の位相を半波長ずらす高さ）が設計の目安
        </p>
      </div>

      {value.blocks.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          ブロックが無い間は平面多層膜として計算されます。ブロックを追加すると、
          多層膜スタックが幅ごとのカラムに分かれ、「上げ」のカラムだけ基板上げの
          台座に乗ります（横方向に周期的に繰り返す構造として解きます）。
        </p>
      ) : (
        <div className="grid gap-2">
          {value.blocks.map((b, i) => (
            <div
              key={b.id}
              className="grid grid-cols-[1fr_auto_auto] items-end gap-2"
            >
              <div className="grid gap-1">
                <Label className="text-xs text-muted-foreground">
                  ブロック{i + 1} の幅 (nm)
                </Label>
                <NumberInput
                  step={10}
                  value={b.widthNm}
                  onChange={(widthNm) => updateBlock(i, { widthNm })}
                />
              </div>
              <label className="flex h-9 cursor-pointer items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={b.raised}
                  onChange={(e) => updateBlock(i, { raised: e.target.checked })}
                  className="h-4 w-4 accent-primary"
                />
                上げ
              </label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeBlock(i)}
                aria-label={`ブロック${i + 1}を削除`}
              >
                削除
              </Button>
            </div>
          ))}
        </div>
      )}

      <Button variant="outline" size="sm" onClick={addBlock}>
        + ブロックを追加
      </Button>
    </div>
  );
}
