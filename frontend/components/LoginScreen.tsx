"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authErrorMessage } from "@/lib/auth-errors";
import { supabase } from "@/lib/supabase";

/** 未ログイン時に計算画面の代わりに出す画面。 */
export function LoginScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const signInWithGoogle = async () => {
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

  // 成功すると onAuthStateChange 経由で AuthGate が計算画面に切り替える。
  const signInWithPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPending(true);
    setError(null);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      setError(authErrorMessage(error));
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
        <CardContent className="grid gap-4">
          <form onSubmit={signInWithPassword} className="grid gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="email">メールアドレス</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="password">パスワード</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <Button type="submit" disabled={pending}>
              ログイン
            </Button>
          </form>

          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <div className="h-px flex-1 bg-border" />
            または
            <div className="h-px flex-1 bg-border" />
          </div>

          <Button variant="outline" onClick={signInWithGoogle} disabled={pending}>
            Google でログイン
          </Button>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>
    </main>
  );
}
