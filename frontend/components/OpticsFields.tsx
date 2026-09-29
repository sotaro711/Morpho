"use client";

import { RotateCw, X } from "lucide-react";
import Link from "next/link";

import { Field } from "@/components/Field";
import { useMaterials } from "@/components/MaterialsProvider";
import { NumberInput } from "@/components/NumberInput";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Optics } from "@/lib/stack";
import { cn } from "@/lib/utils";

type Value = Optics & { name: string };

type Props = {
  value: Value;
  onChange: (patch: Partial<Value>) => void;
};

/**
 * 層・基板の光学定数の入力。既定は n, k を打つだけで、登録した材料は横から選ぶ。
 * 材料を選ぶと n, k の欄が材料名に変わり、× で n, k に戻る（n, k の値は残してあるので復元される）。
 * 親のグリッドの 1 行を占める。
 */
export function OpticsFields({ value, onChange }: Props) {
  const { materials, loading, loadError, reload } = useMaterials();

  if (value.materialId) {
    return <SelectedMaterial value={value} onChange={onChange} />;
  }

  const choose = (id: string) => {
    const material = materials.find((m) => m.id === id);
    if (!material) return;
    // 層名は材料名にそろえ、元の名前は外したときに戻せるよう覚えておく。
    onChange({ materialId: material.id, name: material.name, nameBeforeMaterial: value.name });
  };

  return (
    <div className="col-span-full grid grid-cols-[1fr_1fr_auto] items-end gap-2">
      <Field label="屈折率 n">
        <NumberInput step={0.01} value={value.n} onChange={(n) => onChange({ n })} />
      </Field>
      <Field label="消衰係数 k">
        <NumberInput step={0.01} value={value.k} onChange={(k) => onChange({ k })} />
      </Field>
      {loadError ? (
        <Button type="button" variant="outline" onClick={reload} title={loadError}>
          材料を読み直す
        </Button>
      ) : !loading && materials.length === 0 ? (
        <Button variant="outline" asChild>
          <Link href="/materials">材料を登録</Link>
        </Button>
      ) : (
        // 選ぶための入口なので値は持たない（選んだ瞬間に材料表示へ切り替わる）。
        <Select value="" onValueChange={choose} disabled={loading}>
          <SelectTrigger aria-label="登録した材料から選ぶ">
            <SelectValue placeholder="材料を選ぶ" />
          </SelectTrigger>
          <SelectContent align="end">
            {materials.map((m) => (
              <SelectItem key={m.id} value={m.id}>
                {m.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  );
}

function SelectedMaterial({ value, onChange }: Props) {
  const { materials, loading, loadError, reload } = useMaterials();
  const material = materials.find((m) => m.id === value.materialId);
  // 選んでいた材料が材料ページで削除された。一覧を読めていないときは判断できないので含めない。
  const missing = !loading && !loadError && !material;

  const clear = () =>
    onChange({
      materialId: null,
      // 材料を選んだあとに名前を変えていなければ、選ぶ前の名前に戻す。
      // 削除済みだと材料名と比べられないので、そのときは選ぶ前の名前に戻す。
      name:
        value.nameBeforeMaterial !== undefined && (missing || value.name === material?.name)
          ? value.nameBeforeMaterial
          : value.name,
      nameBeforeMaterial: undefined,
    });

  return (
    <div className="col-span-full grid gap-1">
      <Field label="材料">
        <div
          className={cn(
            "flex h-9 items-center gap-2 rounded-md border px-3 text-sm",
            missing && "border-destructive/50 text-destructive",
          )}
        >
          <span className="min-w-0 flex-1 truncate">
            {material?.name ??
              (missing ? "削除された材料" : loadError ? "材料一覧を読み込めません" : "読み込み中…")}
          </span>
          {loadError ? (
            // 材料はまだあるかもしれないので、外させずに読み直してもらう。
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="-mr-2 h-7 w-7 text-muted-foreground"
              aria-label="材料一覧を読み直す"
              title={loadError}
              onClick={reload}
            >
              <RotateCw className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="-mr-2 h-7 w-7 text-muted-foreground"
              aria-label="材料を外して n, k を入力する"
              onClick={clear}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </Field>
      {missing && (
        <p className="text-xs text-destructive">
          この材料は削除されました。× を押して n, k を入力するか、材料を選び直してください
        </p>
      )}
    </div>
  );
}
