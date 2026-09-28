import type { Middleware } from "openapi-fetch";

import { supabase } from "@/lib/supabase";

// fetch に渡した本文は読み切られて再送できないので、送信前に複製を取っておく。
// キーはリクエスト自体（onRequest と onResponse に同じオブジェクトが渡る）。
const retryCopies = new WeakMap<Request, Request>();

function withToken(request: Request, token: string | undefined): Request {
  if (token) request.headers.set("Authorization", `Bearer ${token}`);
  return request;
}

/**
 * すべての API 呼び出しにログイン中のアクセストークンを付ける。
 *
 * 401 が返ったら、スリープ復帰などで期限が切れただけの可能性があるので、
 * 一度だけトークンを更新して送り直す。それでも 401 ならログアウトし、
 * AuthGate がログイン画面に切り替える。
 */
export const authMiddleware: Middleware = {
  async onRequest({ request }) {
    const { data } = await supabase.auth.getSession();
    withToken(request, data.session?.access_token);
    retryCopies.set(request, request.clone());
    return request;
  },

  async onResponse({ request, response, options }) {
    if (response.status !== 401) return response;

    const copy = retryCopies.get(request);
    const { data, error } = await supabase.auth.refreshSession();
    if (error || !data.session || !copy) {
      await supabase.auth.signOut();
      return response;
    }

    const retried = await options.fetch(withToken(copy, data.session.access_token));
    if (retried.status === 401) await supabase.auth.signOut();
    return retried;
  },
};
