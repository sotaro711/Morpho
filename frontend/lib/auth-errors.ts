import { isAuthError, isAuthRetryableFetchError } from "@supabase/supabase-js";

// Supabase Auth のエラーコードごとの日本語文言。メッセージ文字列は SDK の更新で
// 変わりうるので、判定には code を使う。
const MESSAGES: Record<string, string> = {
  invalid_credentials: "メールアドレスかパスワードが違います",
  email_not_confirmed:
    "メールアドレスの確認が済んでいません。届いた確認メールのリンクを開いてください",
  email_address_invalid: "メールアドレスの形式が正しくありません",
  weak_password: "パスワードが弱すぎます。8 文字以上にしてください",
  otp_expired: "リンクの有効期限が切れています。もう一度メールを送ってください",
  over_request_rate_limit: "試行回数が多すぎます。しばらく待ってから再度お試しください",
  over_email_send_rate_limit:
    "メールの送信回数が多すぎます。しばらく待ってから再度お試しください",
  signup_disabled: "現在、新規登録を受け付けていません",
};

/** Supabase Auth のエラーを画面に出す日本語の文言にする。 */
export function authErrorMessage(error: unknown): string {
  if (isAuthRetryableFetchError(error)) {
    return "通信に失敗しました。ネットワークを確認して再度お試しください";
  }
  if (isAuthError(error) && error.code && error.code in MESSAGES) {
    return MESSAGES[error.code];
  }
  return "エラーが発生しました。時間をおいて再度お試しください";
}
