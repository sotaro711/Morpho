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
        <GoogleLogo />
        Google で続ける
      </Button>
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}

/** Google の「G」ロゴ（ブランドガイドラインの 4 色版）。 */
function GoogleLogo() {
  return (
    <svg viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.33-1.58-5.04-3.7H.96v2.33A9 9 0 0 0 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.96 10.72A5.41 5.41 0 0 1 3.68 9c0-.6.1-1.18.28-1.72V4.95H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.05l3-2.33z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.51.45 3.44 1.35l2.58-2.58A8.97 8.97 0 0 0 9 0 9 9 0 0 0 .96 4.95l3 2.33C4.67 5.16 6.66 3.58 9 3.58z"
      />
    </svg>
  );
}
