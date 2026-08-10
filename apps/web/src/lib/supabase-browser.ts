import {
  createClient,
  type SupabaseClient,
} from "@supabase/supabase-js";


let browserClient:
  SupabaseClient | null = null;


export function getSupabaseBrowserClient():
  SupabaseClient {
  if (browserClient) {
    return browserClient;
  }


  const url =
    process.env
      .NEXT_PUBLIC_SUPABASE_URL;

  const key =
    process.env
      .NEXT_PUBLIC_SUPABASE_ANON_KEY;


  if (!url || !key) {
    throw new Error(
      "Supabase browser configuration is missing.",
    );
  }


  browserClient =
    createClient(
      url,
      key,
      {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
        },
      },
    );


  return browserClient;
}