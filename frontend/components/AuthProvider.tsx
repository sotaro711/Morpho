"use client";

import type { Session } from "@supabase/supabase-js";
import { createContext, useContext, useEffect, useState } from "react";

import { emailLinkVerification } from "@/lib/email-link";
import { supabase } from "@/lib/supabase";

type AuthState = {
  session: Session | null;
  loading: boolean;
  linkError: string | null;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [linkError, setLinkError] = useState<string | null>(null);

  useEffect(() => {
    // 購読直後に INITIAL_SESSION が届くので、初回の確認もこの 1 本で済む。
    const { data } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      if (!emailLinkVerification) setLoading(false);
    });

    let active = true;
    emailLinkVerification?.then((result) => {
      if (!active) return;
      if (!result.ok) setLinkError(result.message);
      setLoading(false);
    });

    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, []);

  return (
    <AuthContext.Provider value={{ session, loading, linkError }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth は AuthProvider の内側で使ってください");
  return ctx;
}
