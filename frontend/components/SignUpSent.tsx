"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { authErrorMessage } from "@/lib/auth-errors";
import { supabase } from "@/lib/supabase";

type Props = { email: string; onBack: () => void };

/** 新規登録の送信後に出す、確認メールの案内と再送。 */
export function SignUpSent({ email, onBack }: Props) {
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const resend = async () => {
    setPending(true);
    const { error } = await supabase.auth.resend({
      type: "signup",
      email,
      options: { emailRedirectTo: window.location.origin },
    });
    setPending(false);
    setMessage(error ? authErrorMessage(error) : "確認メールを再送しました");
  };

  return (
    <div className="grid gap-3 text-sm">
      <p>
        <span className="font-medium">{email}</span> に確認メールを送りました。
        メールのリンクを開くと登録が完了します。
      </p>
      <p className="text-muted-foreground">
        届かない場合は、迷惑メールフォルダも確認してください。
      </p>
      {message && <p className="text-muted-foreground">{message}</p>}
      <Button variant="outline" onClick={resend} disabled={pending}>
        確認メールを再送する
      </Button>
      <Button variant="link" onClick={onBack}>
        ログインに戻る
      </Button>
    </div>
  );
}
