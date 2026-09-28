"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { authErrorMessage } from "@/lib/auth-errors";
import { supabase } from "@/lib/supabase";

/**
 * Google でログインする。初回はそのまま登録になるので、
 * ログインと新規登録のどちらの画面でも同じ文言で出す。
 */
export function GoogleButton() {
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const signIn = async () => {
    setPending(true);
    setError(null);
    // 成功すると Google の画面へ遷移するので、ここに戻るのは失敗したときだけ。
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
    if (error) {
      setError(authErrorMessage(error));
      setPending(false);
    }
  };

  return (
    <div className="grid gap-2">
      <Button variant="outline" onClick={signIn} disabled={pending}>
        Google で続ける
      </Button>
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
