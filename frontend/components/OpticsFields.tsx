"use client";

import { Field } from "@/components/Field";
import { useMaterials } from "@/components/MaterialsProvider";
import { NumberInput } from "@/components/NumberInput";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Optics } from "@/lib/stack";
import { cn } from "@/lib/utils";

const MANUAL = "manual";

type Props = {
  value: Optics;
  /** 材料を選んだときは、名前もその材料名にそろえる。 */
  onChange: (patch: Partial<Optics> & { name?: string }) => void;
  /** 材料の選択欄に付けるクラス（親のグリッドでの幅の調整用）。 */
  selectClassName?: string;
};

/**
 * 層・基板の光学定数の入力。「手入力（n, k）」か「登録した材料」を選ぶ。
 * 材料を選んでいる間は n, k の欄を隠す（値は残し、手入力に戻すと復元する）。
 */
export function OpticsFields({ value, onChange, selectClassName }: Props) {
  const { materials, loading } = useMaterials();
  const selected = value.materialId
    ? materials.find((m) => m.id === value.materialId)
    : undefined;
  // 選んでいた材料が材料ページで削除された。選択を外して選び直してもらう。
  const missing = Boolean(value.materialId) && !loading && !selected;

  const choose = (v: string) => {
    if (v === MANUAL) {
      onChange({ materialId: null });
      return;
    }
    const material = materials.find((m) => m.id === v);
    if (material) onChange({ materialId: material.id, name: material.name });
  };

  return (
    <>
      <div className={cn("grid gap-1", selectClassName)}>
        <Field label="材料">
          <Select
            value={value.materialId ? (selected?.id ?? "") : MANUAL}
            onValueChange={choose}
          >
            <SelectTrigger className="w-full" aria-invalid={missing || undefined}>
              <SelectValue placeholder="材料を選び直してください" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={MANUAL}>手入力（n, k）</SelectItem>
              {materials.length > 0 && <SelectSeparator />}
              {materials.map((m) => (
                <SelectItem key={m.id} value={m.id}>
                  {m.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        {missing && (
          <p className="text-xs text-destructive">
            選んでいた材料は削除されました。材料を選び直してください
          </p>
        )}
      </div>

      {!value.materialId && (
        <>
          <Field label="屈折率 n">
            <NumberInput step={0.01} value={value.n} onChange={(n) => onChange({ n })} />
          </Field>
          <Field label="消衰係数 k">
            <NumberInput step={0.01} value={value.k} onChange={(k) => onChange({ k })} />
          </Field>
        </>
      )}
    </>
  );
}
