"use client";

import { useState } from "react";

import { NewPasswordFields } from "@/components/NewPasswordFields";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authErrorMessage } from "@/lib/auth-errors";
import { validateNewPassword } from "@/lib/password";
import { supabase } from "@/lib/supabase";

type Props = {
  onSignIn: () => void;
  onSent: (email: string) => void;
};

/** メールアドレスでの新規登録。送信後は確認メールの案内に切り替わる。 */
export function SignUpForm({ onSignIn, onSent }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const invalid = validateNewPassword(password, confirm);
    if (invalid) {
      setError(invalid);
      return;
    }

    setPending(true);
    setError(null);
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      // メール内リンクの戻り先。開発は localhost、本番は Cloud Run に自動で分かれる。
      options: { emailRedirectTo: window.location.origin },
    });
    setPending(false);
    if (error) {
      setError(authErrorMessage(error));
      return;
    }
    // メール確認が有効だと、登録済みのアドレスでもアカウントの有無を隠すため成功が返る。
    // その場合は identities が空になるので、ここで見分けて案内する。
    if (data.user?.identities?.length === 0) {
      setError(
        "このメールアドレスは登録済みです。ログインしてください。Google で登録した場合は「Google で続ける」からログインできます",
      );
      return;
    }
    onSent(email);
  };

  return (
    <form onSubmit={submit} className="grid gap-3">
      <div className="grid gap-1.5">
        <Label htmlFor="signup-email">メールアドレス</Label>
        <Input
          id="signup-email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <NewPasswordFields
        password={password}
        confirm={confirm}
        onPasswordChange={setPassword}
        onConfirmChange={setConfirm}
      />
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" disabled={pending}>
        登録する
      </Button>
      <p className="text-center text-sm text-muted-foreground">
        アカウントをお持ちの方は
        <Button type="button" variant="link" className="px-1" onClick={onSignIn}>
          ログイン
        </Button>
      </p>
    </form>
  );
}
