"use client";

import {
  FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  createChatSession,
  getChatHistory,
  sendChatMessage,
} from "@/lib/supportpilot-api";

import {
  clearStoredSession,
  loadStoredSession,
  storeSession,
} from "@/lib/chat-session-storage";

import type {
  ChatHistory,
  ChatSession,
} from "@/lib/chat-types";


type PendingMessage = {
  id: string;
  body: string;
};


export default function CustomerChat() {
  const [session, setSession] =
    useState<ChatSession | null>(null);

  const [history, setHistory] =
    useState<ChatHistory | null>(null);

  const [message, setMessage] =
    useState("");

  const [email, setEmail] =
    useState("");

  const [pending, setPending] =
    useState<PendingMessage | null>(
      null,
    );

  const [isStarting, setIsStarting] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const initialized =
    useRef(false);


  const refreshHistory = useCallback(
    async (
      activeSession: ChatSession,
    ) => {
      const result =
        await getChatHistory(
          activeSession,
        );

      setHistory(result);
    },
    [],
  );

  const initialize = useCallback(
    async () => {
      setIsStarting(true);
      setError(null);

      try {
        let activeSession =
          loadStoredSession();

        if (activeSession) {
          try {
            await refreshHistory(
              activeSession,
            );

            setSession(
              activeSession,
            );

            return;
          } catch {
            clearStoredSession();
            activeSession = null;
          }
        }

        const newSession =
          await createChatSession();

        storeSession(
          newSession,
        );

        setSession(
          newSession,
        );

        await refreshHistory(
          newSession,
        );

      } catch {
        setError(
          "Support chat is temporarily unavailable. Please try again.",
        );
      } finally {
        setIsStarting(false);
      }
    },
    [refreshHistory],
  );

  useEffect(() => {
    if (initialized.current) {
      return;
    }

    initialized.current = true;

    void initialize();
  }, [initialize]);

  async function submitMessage(
    event: FormEvent,
  ) {
    event.preventDefault();

    if (
      !session ||
      !message.trim() ||
      pending
    ) {
      return;
    }

    const outgoing: PendingMessage = {
      id: crypto.randomUUID(),
      body: message.trim(),
    };

    setPending(outgoing);
    setMessage("");
    setError(null);

    try {
      await sendChatMessage(
        session,
        outgoing.id,
        outgoing.body,
        email.trim() || undefined,
      );

      await refreshHistory(
        session,
      );

      setPending(null);

    } catch {
      setError(
        "Your message could not be sent. You can retry without creating a duplicate.",
      );
    }
  }


  async function retryPending() {
    if (
      !session ||
      !pending
    ) {
      return;
    }

    setError(null);

    try {
      await sendChatMessage(
        session,
        pending.id,
        pending.body,
        email.trim() || undefined,
      );

      await refreshHistory(
        session,
      );

      setPending(null);

    } catch {
      setError(
        "SupportPilot still could not send the message. Please try again.",
      );
    }
  }


  if (isStarting) {
    return (
      <div className="flex min-h-130 items-center justify-center rounded-3xl border border-slate-200 bg-white">
        <div className="text-center">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-slate-900" />
          <p className="text-sm text-slate-500">
            Starting secure support session…
          </p>
        </div>
      </div>
    );
  }


  return (
    <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl shadow-slate-200/50">

      <header className="border-b border-slate-200 px-6 py-5">
        <div className="flex items-center justify-between gap-4">

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Northstar Commerce
            </p>

            <h2 className="mt-1 text-xl font-semibold text-slate-950">
              Customer Support
            </h2>
          </div>

          <div className="flex items-center gap-2 text-sm text-slate-600">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
            Online
          </div>

        </div>

        {history?.ticket_reference && (
          <div className="mt-4 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-600">
            Ticket{" "}
            <span className="font-semibold text-slate-900">
              {history.ticket_reference}
            </span>
            {" · "}
            {history.ticket_status}
          </div>
        )}
      </header>


      <div className="h-105 space-y-4 overflow-y-auto bg-slate-50/60 px-6 py-5">

        {history?.messages.length === 0 &&
          !pending && (
            <div className="mx-auto max-w-sm pt-16 text-center">
              <h3 className="text-lg font-semibold text-slate-900">
                How can we help?
              </h3>

              <p className="mt-2 text-sm leading-6 text-slate-500">
                Ask about an order, shipping,
                returns, products or another
                support issue.
              </p>
            </div>
          )}


        {history?.messages.map(
          (item) => {
            const customer =
              item.sender_type ===
              "customer";

            return (
              <div
                key={item.id}
                className={
                  customer
                    ? "flex justify-end"
                    : "flex justify-start"
                }
              >
                <div
                  className={[
                    "max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-6",
                    customer
                      ? "rounded-br-md bg-slate-950 text-white"
                      : "rounded-bl-md border border-slate-200 bg-white text-slate-800",
                  ].join(" ")}
                >
                  {item.body}
                </div>
              </div>
            );
          },
        )}


        {pending && (
          <div className="flex justify-end">
            <div className="max-w-[82%] rounded-2xl rounded-br-md bg-slate-800 px-4 py-3 text-sm text-white opacity-70">
              {pending.body}

              <div className="mt-2 text-[11px] text-slate-300">
                Sending…
              </div>
            </div>
          </div>
        )}

      </div>


      <div className="border-t border-slate-200 p-5">

        {error && (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            <p>
              {error}
            </p>

            {pending && (
              <button
                type="button"
                onClick={() =>
                  void retryPending()
                }
                className="mt-2 font-semibold underline underline-offset-2"
              >
                Retry message
              </button>
            )}
          </div>
        )}


        <label className="mb-4 block">
          <span className="mb-1.5 block text-xs font-medium text-slate-600">
            Email for order support
            <span className="font-normal text-slate-400">
              {" "}
              (optional)
            </span>
          </span>

          <input
            type="email"
            value={email}
            onChange={(event) =>
              setEmail(
                event.target.value,
              )
            }
            placeholder="you@example.com"
            className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none transition focus:border-slate-400"
          />
        </label>


        <form
          onSubmit={submitMessage}
          className="flex gap-3"
        >
          <textarea
            value={message}
            onChange={(event) =>
              setMessage(
                event.target.value,
              )
            }
            placeholder="Type your message…"
            rows={2}
            disabled={
              !session ||
              pending !== null
            }
            className="min-h-14 flex-1 resize-none rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 disabled:bg-slate-50"
          />

          <button
            type="submit"
            disabled={
              !session ||
              pending !== null ||
              !message.trim()
            }
            className="self-end rounded-2xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Send
          </button>
        </form>

        <p className="mt-3 text-center text-[11px] leading-5 text-slate-400">
          Never send payment card details
          or sensitive financial information
          through chat.
        </p>

      </div>
    </div>
  );
}