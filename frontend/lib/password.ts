export const MIN_PASSWORD_LENGTH = 8;

export function validateNewPassword(password: string, confirm: string): string | null {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `パスワードは ${MIN_PASSWORD_LENGTH} 文字以上にしてください`;
  }
  if (password !== confirm) return "確認用のパスワードが一致しません";
  return null;
}
