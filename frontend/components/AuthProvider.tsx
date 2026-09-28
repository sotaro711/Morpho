"use client";

import type { Session } from "@supabase/supabase-js";
import { createContext, useContext, useEffect, useState } from "react";

import { verifyEmailLinkOnce } from "@/lib/email-link";
import { supabase } from "@/lib/supabase";

type AuthState = {
  session: Session | null;
  /** 保存済みセッションとメール内リンクの確認が終わるまで true。ログイン画面のちらつき防止に使う。 */
  loading: boolean;
  /** パスワード再設定メールのリンクから開かれ、新しいパスワードの入力待ちのとき true。 */
  recovering: boolean;
  /** メール内リンクの検証に失敗したときの文言（期限切れなど）。 */
  linkError: string | null;
};

const AuthContext = createContext<AuthState | null>(null);

/** ログイン状態を購読し、子コンポーネントに配る。 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [recovering, setRecovering] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);

  useEffect(() => {
    const linkVerification = verifyEmailLinkOnce();

    // 購読直後に INITIAL_SESSION が届くので、初回の確認もこの 1 本で済む。
    // メール内リンクの検証中は、その結果が出るまで読み込み中のままにする。
    const { data } = supabase.auth.onAuthStateChange((event, next) => {
      setSession(next);
      if (event === "PASSWORD_RECOVERY") setRecovering(true);
      if (event === "SIGNED_OUT") setRecovering(false);
      if (!linkVerification) setLoading(false);
    });

    let active = true;
    linkVerification?.then((error) => {
      if (!active) return;
      setLinkError(error);
      setLoading(false);
    });

    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, []);

  return (
    <AuthContext.Provider value={{ session, loading, recovering, linkError }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth は AuthProvider の内側で使ってください");
  return ctx;
}
