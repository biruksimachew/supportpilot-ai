"use client";


import {
  useEffect,
  useState,
} from "react";

import type {
  FormEvent,
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

    let active =
      true;


    async function checkSession() {

      try {

        const supabase =
          getSupabaseBrowserClient();


        const {
          data,
          error:
            sessionError,
        } =
          await supabase.auth
            .getSession();


        if (!active) {
          return;
        }


        if (
          !sessionError
          &&
          data.session
        ) {
          router.replace(
            "/staff",
          );

          return;
        }

      } finally {

        if (active) {
          setChecking(
            false,
          );
        }
      }
    }


    void checkSession();


    return () => {
      active = false;
    };

  }, [
    router,
  ]);


  async function submit(
    event: FormEvent<
      HTMLFormElement
    >,
  ) {

    event.preventDefault();


    if (loading) {
      return;
    }


    setLoading(
      true,
    );

    setError(
      null,
    );


    try {

      const supabase =
        getSupabaseBrowserClient();


      const {
        data,
        error:
          signInError,
      } =
        await supabase.auth
          .signInWithPassword(
            {
              email:
                email
                  .trim()
                  .toLowerCase(),

              password,
            },
          );


      if (
        signInError
        ||
        !data.session
      ) {
        setError(
          "Invalid staff email or password.",
        );

        return;
      }


      router.replace(
        "/staff",
      );

      router.refresh();

    } catch {

      setError(
        (
          "Staff sign-in is "
          + "temporarily unavailable."
        ),
      );

    } finally {

      setLoading(
        false,
      );
    }
  }


  if (checking) {

    return (
      <div
        className={
          "rounded-xl "
          + "border border-slate-200 "
          + "bg-slate-50 "
          + "px-4 py-4 "
          + "text-sm text-slate-500"
        }
      >
        Checking staff session...
      </div>
    );
  }


  return (
    <form
      onSubmit={
        submit
      }
      className="space-y-5"
    >

      {error && (
        <div
          role="alert"
          className={
            "rounded-xl "
            + "border border-red-200 "
            + "bg-red-50 "
            + "px-4 py-3 "
            + "text-sm text-red-800"
          }
        >
          {error}
        </div>
      )}


      <label className="block">

        <span
          className={
            "mb-2 block "
            + "text-sm font-medium "
            + "text-slate-700"
          }
        >
          Staff email
        </span>


        <input
          type="email"

          autoComplete="username"

          required

          disabled={
            loading
          }

          value={
            email
          }

          onChange={
            (event) =>
              setEmail(
                event.target.value,
              )
          }

          className={
            "w-full rounded-xl "
            + "border border-slate-200 "
            + "bg-white "
            + "px-4 py-3 "
            + "text-slate-950 "
            + "outline-none transition "
            + "placeholder:text-slate-400 "
            + "focus:border-slate-400 "
            + "focus:ring-4 "
            + "focus:ring-slate-100 "
            + "disabled:cursor-not-allowed "
            + "disabled:bg-slate-50"
          }

          placeholder={
            "support.manager@example.com"
          }
        />

      </label>


      <label className="block">

        <span
          className={
            "mb-2 block "
            + "text-sm font-medium "
            + "text-slate-700"
          }
        >
          Password
        </span>


        <input
          type="password"

          autoComplete={
            "current-password"
          }

          required

          disabled={
            loading
          }

          value={
            password
          }

          onChange={
            (event) =>
              setPassword(
                event.target.value,
              )
          }

          className={
            "w-full rounded-xl "
            + "border border-slate-200 "
            + "bg-white "
            + "px-4 py-3 "
            + "text-slate-950 "
            + "outline-none transition "
            + "focus:border-slate-400 "
            + "focus:ring-4 "
            + "focus:ring-slate-100 "
            + "disabled:cursor-not-allowed "
            + "disabled:bg-slate-50"
          }
        />

      </label>


      <button
        type="submit"

        disabled={
          loading
        }

        className={
          "w-full rounded-xl "
          + "bg-slate-950 "
          + "px-5 py-3 "
          + "font-semibold text-white "
          + "transition "
          + "hover:bg-slate-800 "
          + "focus:outline-none "
          + "focus:ring-4 "
          + "focus:ring-slate-200 "
          + "disabled:cursor-not-allowed "
          + "disabled:opacity-50"
        }
      >
        {
          loading
            ? "Signing in..."
            : "Sign in to console"
        }
      </button>


      <p
        className={
          "text-center "
          + "text-xs leading-5 "
          + "text-slate-400"
        }
      >
        Authorized Northstar support
        staff only.
      </p>

    </form>
  );
}