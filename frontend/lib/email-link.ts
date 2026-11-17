import { authErrorMessage } from "@/lib/auth-errors";
import { supabase } from "@/lib/supabase";

export type EmailLinkResult = { ok: true } | { ok: false; message: string };

function isSupportedType(type: string): type is "email" {
  return type === "email";
}

function takeEmailLink(): { tokenHash: string; type: string } | null {
  const url = new URL(window.location.href);
  const tokenHash = url.searchParams.get("token_hash");
  const type = url.searchParams.get("type");
  if (!tokenHash || !type) return null;

  url.searchParams.delete("token_hash");
  url.searchParams.delete("type");
  window.history.replaceState(null, "", url.pathname + url.search + url.hash);
  return { tokenHash, type };
}

async function verify(link: { tokenHash: string; type: string }): Promise<EmailLinkResult> {
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

// トークンは使い捨てで、何度走っても安全な effect の形にはできないため、モジュールの読み込み時に始める。
export const emailLinkVerification: Promise<EmailLinkResult> | null =
  typeof window === "undefined" ? null : startVerification();
