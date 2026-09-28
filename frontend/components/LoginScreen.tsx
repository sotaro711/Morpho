"use client";

import { useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { GoogleButton } from "@/components/GoogleButton";
import { SignInForm } from "@/components/SignInForm";
import { SignUpForm } from "@/components/SignUpForm";
import { SignUpSent } from "@/components/SignUpSent";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type View =
  | { name: "signIn" }
  | { name: "signUp" }
  | { name: "sent"; email: string };

/** 未ログイン時に計算画面の代わりに出す画面。枠と表示の切り替えだけを持つ。 */
export function LoginScreen() {
  const [view, setView] = useState<View>({ name: "signIn" });
  const { linkError } = useAuth();

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-xl">🦋 Morpho</CardTitle>
          <p className="text-sm text-muted-foreground">
            {view.name === "signUp"
              ? "アカウントを作成"
              : "多層膜の反射スペクトルと構造色のシミュレータ"}
          </p>
        </CardHeader>
        <CardContent className="grid gap-4">
          {linkError && (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {linkError}
            </p>
          )}
          {view.name === "signIn" && (
            <SignInForm onSignUp={() => setView({ name: "signUp" })} />
          )}
          {view.name === "signUp" && (
            <SignUpForm
              onSignIn={() => setView({ name: "signIn" })}
              onSent={(email) => setView({ name: "sent", email })}
            />
          )}
          {view.name === "sent" && (
            <SignUpSent
              email={view.email}
              onBack={() => setView({ name: "signIn" })}
            />
          )}

          {view.name !== "sent" && (
            <>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <div className="h-px flex-1 bg-border" />
                または
                <div className="h-px flex-1 bg-border" />
              </div>
              <GoogleButton />
            </>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
