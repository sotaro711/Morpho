"use client";

import { useAuth } from "@/components/AuthProvider";
import { LoginScreen } from "@/components/LoginScreen";

/**
 * 前面ガード。未ログインなら子の代わりにログイン画面を出す。
 *
 * 静的書き出しなのでサーバー側で弾けず、これは表示の切り替えにすぎない。
 * 本当の防御は API 側の認証（未ログインなら 401）が担う。
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        読み込み中…
      </main>
    );
  }
  if (!session) return <LoginScreen />;
  return <>{children}</>;
}
