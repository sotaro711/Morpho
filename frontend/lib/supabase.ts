import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

if (!url || !publishableKey) {
  throw new Error(
    "NEXT_PUBLIC_SUPABASE_URL と NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY を設定してください",
  );
}

// supabase-js の既定は implicit フローなので、PKCE を明示する。
// Google から戻ったときの ?code= は detectSessionInUrl(既定で有効)がブラウザ内で交換する。
export const supabase = createClient(url, publishableKey, {
  auth: { flowType: "pkce" },
});
