"use client";

import { LogOut } from "lucide-react";

import { useAuth } from "@/components/AuthProvider";
import { Button } from "@/components/ui/button";
import { supabase } from "@/lib/supabase";

/** ヘッダー右端のログイン中ユーザー表示とログアウト。 */
export function UserMenu() {
  const { session } = useAuth();

  return (
    <div className="ml-auto flex items-center gap-3">
      <span className="text-sm text-muted-foreground">
        {session?.user.email}
      </span>
      <Button
        variant="outline"
        size="sm"
        onClick={() => supabase.auth.signOut()}
      >
        <LogOut />
        ログアウト
      </Button>
    </div>
  );
}
