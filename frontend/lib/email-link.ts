import type { EmailOtpType } from "@supabase/supabase-js";

import { authErrorMessage } from "@/lib/auth-errors";
import { supabase } from "@/lib/supabase";

// supabase/templates/ の確認メールのリンクが付ける type。
const LINK_TYPES: EmailOtpType[] = ["email"];

/** URL にメール内リンクのトークンがあれば取り出し、URL からは消す。 */
function takeEmailLink(): { tokenHash: string; type: EmailOtpType } | null {
  const url = new URL(window.location.href);
  const tokenHash = url.searchParams.get("token_hash");
  const type = url.searchParams.get("type");
  if (!tokenHash || !type) return null;

  // トークンを履歴やブックマークに残さない。
  url.searchParams.delete("token_hash");
  url.searchParams.delete("type");
  window.history.replaceState(null, "", url.pathname + url.search + url.hash);

  if (!LINK_TYPES.includes(type as EmailOtpType)) return null;
  return { tokenHash, type: type as EmailOtpType };
}

// 開発時の StrictMode では effect が 2 回走る。トークンは 1 回しか使えないので、
// 検証はモジュールで 1 度だけ行い、2 回目以降は同じ結果を返す。
let verification: Promise<string | null> | null = null;

/**
 * メール内リンクから開かれていればトークンを検証してログインさせる。
 * リンクから開かれていなければ null。失敗したら画面に出す文言を返す。
 * 成功時のセッション反映は onAuthStateChange に届く。
 */
export function verifyEmailLinkOnce(): Promise<string | null> | null {
  if (verification) return verification;
  const link = takeEmailLink();
  if (!link) return null;
  verification = supabase.auth
    .verifyOtp({ token_hash: link.tokenHash, type: link.type })
    .then(({ error }) => (error ? authErrorMessage(error) : null));
  return verification;
}
