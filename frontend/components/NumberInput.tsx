"use client";

import { useState } from "react";

import { Input } from "@/components/ui/input";

type Props = {
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  max?: number;
  className?: string;
};

export function NumberInput({ value, onChange, step, min, max, className }: Props) {
  const [text, setText] = useState(() => String(value));
  const [prevValue, setPrevValue] = useState(value);

  if (value !== prevValue) {
    setPrevValue(value);
    if (Number(text) !== value) setText(String(value));
  }

  return (
    <Input
      type="number"
      inputMode="decimal"
      value={text}
      step={step}
      min={min}
      max={max}
      className={className}
      onChange={(e) => {
        const t = e.target.value;
        setText(t);
        const n = Number(t);
        if (t.trim() !== "" && Number.isFinite(n)) onChange(n);
      }}
      onBlur={() => {
        const n = Number(text);
        setText(text.trim() === "" || !Number.isFinite(n) ? String(value) : String(n));
      }}
    />
  );
}
