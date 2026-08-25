"use client";

import { NumberInput } from "@/components/NumberInput";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Polarization } from "@/lib/api/client";
import type { Settings } from "@/lib/stack";

type Props = {
  value: Settings;
  onChange: (patch: Partial<Settings>) => void;
};

function NumberField({
  label,
  value,
  onChange,
  step,
  min,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
}) {
  return (
    <div className="grid gap-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <NumberInput value={value} step={step} min={min} onChange={onChange} />
    </div>
  );
}

export function SettingsForm({ value, onChange }: Props) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <NumberField
        label="波長 min (nm)"
        value={value.wlMin}
        onChange={(v) => onChange({ wlMin: v })}
      />
      <NumberField
        label="波長 max (nm)"
        value={value.wlMax}
        onChange={(v) => onChange({ wlMax: v })}
      />
      <NumberField
        label="波長点数"
        value={value.wlPoints}
        min={1}
        onChange={(v) => onChange({ wlPoints: v })}
      />
      <NumberField
        label="入射角 θ (deg)"
        value={value.thetaDeg}
        step={1}
        onChange={(v) => onChange({ thetaDeg: v })}
      />
      <div className="grid gap-1.5">
        <Label className="text-xs text-muted-foreground">偏光</Label>
        <Select
          value={value.pol}
          onValueChange={(v) => onChange({ pol: v as Polarization })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="s">s (TE)</SelectItem>
            <SelectItem value="p">p (TM)</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
