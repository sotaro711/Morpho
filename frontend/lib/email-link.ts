import { authErrorMessage } from "@/lib/auth-errors";
import { supabase } from "@/lib/supabase";

/** メール内リンクの検証結果。 */
export type EmailLinkResult = { ok: true } | { ok: false; message: string };

// supabase/templates/ の確認メールのリンクが付ける type。
function isSupportedType(type: string): type is "email" {
  return type === "email";
}

/** URL にメール内リンクのトークンがあれば取り出し、URL からは消す。 */
function takeEmailLink(): { tokenHash: string; type: string } | null {
  const url = new URL(window.location.href);
  const tokenHash = url.searchParams.get("token_hash");
  const type = url.searchParams.get("type");
  if (!tokenHash || !type) return null;

  // トークンを履歴やブックマークに残さない。
  url.searchParams.delete("token_hash");
  url.searchParams.delete("type");
  window.history.replaceState(null, "", url.pathname + url.search + url.hash);
  return { tokenHash, type };
}

async function verify(link: { tokenHash: string; type: string }): Promise<EmailLinkResult> {
  // 黙ってログイン画面に戻すと理由が分からないので、未対応の種類は案内する。
  // Supabase 側に残っている再設定メール（type=recovery）のリンクもここに来る。
  if (!isSupportedType(link.type)) {
    return { ok: false, message: "このリンクには対応していません" };
  }
  const { error } = await supabase.auth.verifyOtp({
    token_hash: link.tokenHash,
    type: link.type,
  });
  return error ? { ok: false, message: authErrorMessage(error) } : { ok: true };
}

function startVerification(): Promise<EmailLinkResult> | null {
  const link = takeEmailLink();
  return link ? verify(link) : null;
}

/**
 * メール内リンクから開かれていれば、その検証の結果。開かれていなければ null。
 * 成功時のセッション反映は onAuthStateChange に届く。
 *
 * アプリ起動時に 1 度だけ行う初期化なので、effect ではなくモジュールの読み込み時に始める。
 * トークンは使い捨てで、何度走っても安全な effect の形にはできないため。
 * サーバー側のビルド時は window がないので何もしない。
 */
export const emailLinkVerification: Promise<EmailLinkResult> | null =
  typeof window === "undefined" ? null : startVerification();
