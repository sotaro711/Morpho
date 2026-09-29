"use client";

import { FileText, Upload, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Props = {
  file: File | null;
  onChange: (file: File | null) => void;
  accept: string;
  /** 枠の中に小さく出す補足（受け付ける形式など）。 */
  hint?: string;
  label: string;
};

/**
 * ファイルをドラッグして置くか、クリックして選ぶ枠。選んだ後はファイル名と × を出す。
 * ブラウザ標準のファイル欄（「選択されていません」）は見づらいので、input は枠の中に隠す。
 * ドロップでは accept が効かないので、形式の検証は読み取る側に任せる。
 */
export function FileDropZone({ file, onChange, accept, hint, label }: Props) {
  const [dragging, setDragging] = useState(false);

  if (file) {
    return (
      <div className="flex h-10 items-center gap-2 rounded-lg border px-3 text-sm">
        <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className="min-w-0 flex-1 truncate">{file.name}</span>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="-mr-2 h-7 w-7 text-muted-foreground"
          aria-label="ファイルの選択を取り消す"
          onClick={() => onChange(null)}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  return (
    <label
      className={cn(
        "flex cursor-pointer flex-col items-center gap-1 rounded-lg border border-dashed px-4 py-6 text-center transition-colors",
        "hover:bg-muted/50 focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50",
        dragging && "border-primary bg-primary/5",
      )}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        onChange(e.dataTransfer.files[0] ?? null);
      }}
    >
      <Upload className="h-5 w-5 text-muted-foreground" />
      <span className="text-sm">ファイルをドラッグ、またはクリックして選択</span>
      {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
      <input
        type="file"
        accept={accept}
        aria-label={label}
        className="sr-only"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
    </label>
  );
}
