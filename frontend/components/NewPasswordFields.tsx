"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MIN_PASSWORD_LENGTH } from "@/lib/password";

type Props = {
  password: string;
  confirm: string;
  onPasswordChange: (value: string) => void;
  onConfirmChange: (value: string) => void;
};

/** 新しいパスワードと確認用の 2 欄。 */
export function NewPasswordFields({
  password,
  confirm,
  onPasswordChange,
  onConfirmChange,
}: Props) {
  return (
    <>
      <div className="grid gap-1.5">
        <Label htmlFor="new-password">パスワード</Label>
        <Input
          id="new-password"
          type="password"
          autoComplete="new-password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          value={password}
          onChange={(e) => onPasswordChange(e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          {MIN_PASSWORD_LENGTH} 文字以上
        </p>
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="confirm-password">パスワード(確認)</Label>
        <Input
          id="confirm-password"
          type="password"
          autoComplete="new-password"
          required
          value={confirm}
          onChange={(e) => onConfirmChange(e.target.value)}
        />
      </div>
    </>
  );
}
