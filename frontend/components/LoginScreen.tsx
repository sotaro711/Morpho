"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { supabase } from "@/lib/supabase";

/** 未ログイン時に計算画面の代わりに出す画面。 */
export function LoginScreen() {
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
      setError(error.message);
      setPending(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-xl">🦋 Morpho</CardTitle>
          <p className="text-sm text-muted-foreground">
            多層膜の反射スペクトルと構造色のシミュレータ
          </p>
        </CardHeader>
        <CardContent className="grid gap-3">
          <Button onClick={signIn} disabled={pending}>
            {pending ? "Google に移動中…" : "Google でログイン"}
          </Button>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>
    </main>
  );
}
