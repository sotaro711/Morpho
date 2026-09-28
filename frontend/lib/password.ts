// supabase/config.toml の minimum_password_length と揃える。
export const MIN_PASSWORD_LENGTH = 8;

/** 新しいパスワードと確認用の入力を検証する。問題なければ null。 */
export function validateNewPassword(password: string, confirm: string): string | null {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `パスワードは ${MIN_PASSWORD_LENGTH} 文字以上にしてください`;
  }
  if (password !== confirm) return "確認用のパスワードが一致しません";
  return null;
}
