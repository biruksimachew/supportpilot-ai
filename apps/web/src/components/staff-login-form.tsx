"use client";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  getSupabaseBrowserClient,
} from "@/lib/supabase-browser";



export default function StaffLoginForm() {
  const router =
    useRouter();

  const [email, setEmail] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [checking, setChecking] =
    useState(true);

  const [error, setError] =
    useState<string | null>(
      null,
    );


  useEffect(() => {
    async function checkSession() {
      try {
        const supabase =
          getSupabaseBrowserClient();

        const {
          data,
        } =
          await supabase.auth
            .getSession();

        if (data.session) {
          router.replace(
            "/staff",
          );

          return;
        }
      } finally {
        setChecking(false);
      }
    }

    void checkSession();
  }, [router]);


  async function submit(
    event: FormEvent,
  ) {
    event.preventDefault();

    setLoading(true);
    setError(null);


    try {
      const supabase =
        getSupabaseBrowserClient();

      const {
        error:
          signInError,
      } =
        await supabase.auth
          .signInWithPassword({
            email:
              email.trim(),

            password,
          });


      if (signInError) {
        setError(
          "Invalid email or password.",
        );

        return;
      }


      router.replace(
        "/staff",
      );

      router.refresh();

    } catch {
      setError(
        "Staff sign-in is temporarily unavailable.",
      );

    } finally {
      setLoading(false);
    }
  }


  if (checking) {
    return (
      <div className="text-sm text-slate-500">
        Checking staff session…
      </div>
    );
  }


  return (
    <form
      onSubmit={submit}
      className="space-y-5"
    >
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}


      <label className="block">
        <span className="mb-2 block text-sm font-medium text-slate-700">
          Staff email
        </span>

        <input
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(event) =>
            setEmail(
              event.target.value,
            )
          }
          className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-950 outline-none transition focus:border-slate-400"
          placeholder="agent@northstar.demo"
        />
      </label>


      <label className="block">
        <span className="mb-2 block text-sm font-medium text-slate-700">
          Password
        </span>

        <input
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) =>
            setPassword(
              event.target.value,
            )
          }
          className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-950 outline-none transition focus:border-slate-400"
        />
      </label>


      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
      >
        {loading
          ? "Signing in…"
          : "Sign in"}
      </button>
    </form>
  );
}