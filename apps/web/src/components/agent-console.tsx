"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  getSupabaseBrowserClient,
} from "@/lib/supabase-browser";

import {
  getAgentQueue,
  getAgentTicket,
  StaffApiError,
} from "@/lib/staff-api";

import type {
  AgentQueueItem,
  AgentTicketDetail,
} from "@/lib/staff-types";


export default function AgentConsole() {
  const router =
    useRouter();

  const [accessToken, setAccessToken] =
    useState<string | null>(
      null,
    );

  const [staffEmail, setStaffEmail] =
    useState("");

  const [tickets, setTickets] =
    useState<AgentQueueItem[]>(
      [],
    );

  const [selected, setSelected] =
    useState<AgentTicketDetail | null>(
      null,
    );

  const [statusFilter, setStatusFilter] =
    useState("");

  const [priorityFilter, setPriorityFilter] =
    useState("");

  const [channelFilter, setChannelFilter] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const [detailLoading, setDetailLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(
      null,
    );


  const handleAuthFailure =
    useCallback(
      async () => {
        const supabase =
          getSupabaseBrowserClient();

        await supabase.auth.signOut();

        router.replace(
          "/staff/login",
        );
      },
      [router],
    );


  const loadQueue =
    useCallback(
      async (
        token: string,
      ) => {
        try {
          const result =
            await getAgentQueue(
              token,
              {
                status:
                  statusFilter
                  || undefined,

                priority:
                  priorityFilter
                  || undefined,

                channel:
                  channelFilter
                  || undefined,
              },
            );

          setTickets(
            result.items,
          );

          setError(null);

        } catch (caught) {
          if (
            caught
              instanceof StaffApiError
            &&
            (
              caught.status === 401
              ||
              caught.status === 403
            )
          ) {
            await handleAuthFailure();
            return;
          }

          setError(
            "The support queue could not be loaded.",
          );
        }
      },
      [
        channelFilter,
        handleAuthFailure,
        priorityFilter,
        statusFilter,
      ],
    );


  useEffect(() => {
    let cancelled =
      false;


    async function initialize() {
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


        if (
          sessionError
          ||
          !data.session
        ) {
          router.replace(
            "/staff/login",
          );

          return;
        }


        if (cancelled) {
          return;
        }


        setAccessToken(
          data.session
            .access_token,
        );

        setStaffEmail(
          data.session.user.email
          ?? "",
        );


        await loadQueue(
          data.session
            .access_token,
        );

      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }


    void initialize();


    return () => {
      cancelled = true;
    };
  }, [
    loadQueue,
    router,
  ]);


  async function openTicket(
    ticketId: string,
  ) {
    if (!accessToken) {
      return;
    }


    setDetailLoading(true);
    setError(null);


    try {
      const detail =
        await getAgentTicket(
          accessToken,
          ticketId,
        );

      setSelected(
        detail,
      );

    } catch (caught) {
      if (
        caught
          instanceof StaffApiError
        &&
        (
          caught.status === 401
          ||
          caught.status === 403
        )
      ) {
        await handleAuthFailure();
        return;
      }

      setError(
        "The ticket workspace could not be loaded.",
      );

    } finally {
      setDetailLoading(false);
    }
  }


  async function logout() {
    const supabase =
      getSupabaseBrowserClient();

    await supabase.auth.signOut();

    router.replace(
      "/staff/login",
    );
  }


  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 text-sm text-slate-500">
        Loading support queue…
      </div>
    );
  }


  return (
    <main className="min-h-screen bg-slate-100">

      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="mx-auto flex max-w-375 items-center justify-between gap-6">

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              SupportPilot AI
            </p>

            <h1 className="mt-1 text-xl font-semibold text-slate-950">
              Agent Console
            </h1>
          </div>


          <div className="flex items-center gap-4">

            <span className="hidden text-sm text-slate-500 sm:block">
              {staffEmail}
            </span>

            <button
              type="button"
              onClick={() =>
                void logout()
              }
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Sign out
            </button>

          </div>

        </div>
      </header>


      <div className="mx-auto grid max-w-375 gap-5 p-5 lg:grid-cols-[440px_1fr]">

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">

          <div className="border-b border-slate-200 p-4">

            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-slate-950">
                Support queue
              </h2>

              <span className="text-xs text-slate-500">
                {tickets.length} shown
              </span>
            </div>


            <div className="mt-4 grid grid-cols-3 gap-2">

              <select
                value={statusFilter}
                onChange={(event) =>
                  setStatusFilter(
                    event.target.value,
                  )
                }
                className="rounded-lg border border-slate-200 px-2 py-2 text-xs"
              >
                <option value="">
                  All status
                </option>
                <option value="NEW">
                  New
                </option>
                <option value="REVIEW_REQUIRED">
                  Review
                </option>
                <option value="WAITING_CUSTOMER">
                  Waiting
                </option>
                <option value="FAILED">
                  Failed
                </option>
              </select>


              <select
                value={priorityFilter}
                onChange={(event) =>
                  setPriorityFilter(
                    event.target.value,
                  )
                }
                className="rounded-lg border border-slate-200 px-2 py-2 text-xs"
              >
                <option value="">
                  All priority
                </option>
                <option value="P1">
                  P1
                </option>
                <option value="P2">
                  P2
                </option>
                <option value="P3">
                  P3
                </option>
                <option value="P4">
                  P4
                </option>
              </select>


              <select
                value={channelFilter}
                onChange={(event) =>
                  setChannelFilter(
                    event.target.value,
                  )
                }
                className="rounded-lg border border-slate-200 px-2 py-2 text-xs"
              >
                <option value="">
                  All channels
                </option>
                <option value="chat">
                  Chat
                </option>
                <option value="email">
                  Email
                </option>
              </select>

            </div>

          </div>


          <div className="max-h-[calc(100vh-190px)] overflow-y-auto">

            {tickets.length === 0 && (
              <div className="p-8 text-center text-sm text-slate-500">
                No tickets match this queue.
              </div>
            )}


            {tickets.map(
              (ticket) => (
                <button
                  type="button"
                  key={ticket.id}
                  onClick={() =>
                    void openTicket(
                      ticket.id,
                    )
                  }
                  className="block w-full border-b border-slate-100 p-4 text-left transition hover:bg-slate-50"
                >

                  <div className="flex items-start justify-between gap-4">

                    <div>
                      <p className="text-sm font-semibold text-slate-950">
                        {ticket.reference}
                      </p>

                      <p className="mt-1 text-xs text-slate-500">
                        {ticket.channel}
                        {" · "}
                        {ticket.status}
                      </p>
                    </div>


                    <span className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">
                      {ticket.priority}
                    </span>

                  </div>


                  <p className="mt-3 line-clamp-2 text-sm leading-5 text-slate-600">
                    {ticket.last_message_body
                      ?? "No messages"}
                  </p>


                  <div className="mt-3 flex items-center justify-between gap-3 text-xs text-slate-400">

                    <span>
                      {ticket.customer_name
                        ?? ticket.customer_email
                        ?? "Unverified customer"}
                    </span>

                    <span>
                      {ticket.message_count} msg
                    </span>

                  </div>

                </button>
              ),
            )}

          </div>

        </section>


        <section className="min-h-175 rounded-2xl border border-slate-200 bg-white">

          {!selected && !detailLoading && (
            <div className="flex h-full min-h-175 items-center justify-center p-8 text-center">

              <div>
                <h2 className="text-xl font-semibold text-slate-900">
                  Select a ticket
                </h2>

                <p className="mt-2 text-sm text-slate-500">
                  Conversation and support context will appear here.
                </p>
              </div>

            </div>
          )}


          {detailLoading && (
            <div className="flex min-h-175 items-center justify-center text-sm text-slate-500">
              Loading ticket…
            </div>
          )}


          {selected && !detailLoading && (
            <div>

              <header className="border-b border-slate-200 p-6">

                <div className="flex flex-wrap items-start justify-between gap-5">

                  <div>
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                      Ticket
                    </p>

                    <h2 className="mt-1 text-2xl font-semibold text-slate-950">
                      {selected.reference}
                    </h2>

                    <p className="mt-2 text-sm text-slate-500">
                      {selected.channel}
                      {" · "}
                      {selected.status}
                      {" · "}
                      {selected.priority}
                    </p>
                  </div>


                  <div className="text-right text-sm">

                    <p className="font-medium text-slate-900">
                      {selected.customer_name
                        ?? "Unverified customer"}
                    </p>

                    <p className="mt-1 text-slate-500">
                      {selected.customer_email
                        ?? "No verified email"}
                    </p>

                  </div>

                </div>

              </header>


              {error && (
                <div className="m-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
                  {error}
                </div>
              )}


              <div className="grid xl:grid-cols-[1fr_330px]">

                <div className="border-r border-slate-200 p-6">

                  <h3 className="mb-5 font-semibold text-slate-900">
                    Conversation
                  </h3>


                  <div className="space-y-4">

                    {selected.messages.map(
                      (message) => (
                        <div
                          key={message.id}
                          className={[
                            "rounded-2xl p-4 text-sm leading-6",
                            message.is_internal
                              ? "border border-amber-200 bg-amber-50"
                              : message.sender_type
                                  === "customer"
                                ? "bg-slate-100"
                                : "border border-slate-200 bg-white",
                          ].join(" ")}
                        >

                          <div className="mb-2 flex items-center justify-between text-[11px] uppercase tracking-wide text-slate-400">

                            <span>
                              {message.is_internal
                                ? "Internal note"
                                : message.sender_type}
                            </span>

                            <span>
                              {new Date(
                                message.sent_at,
                              ).toLocaleString()}
                            </span>

                          </div>

                          {message.body}

                        </div>
                      ),
                    )}

                  </div>

                </div>


                <aside className="space-y-6 p-6">

                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">
                      Decision
                    </h3>

                    <dl className="mt-3 space-y-2 text-sm">

                      <div className="flex justify-between gap-4">
                        <dt className="text-slate-500">
                          Intent
                        </dt>

                        <dd className="font-medium text-slate-900">
                          {selected.intent
                            ?? "Not classified"}
                        </dd>
                      </div>


                      <div className="flex justify-between gap-4">
                        <dt className="text-slate-500">
                          Confidence
                        </dt>

                        <dd className="font-medium text-slate-900">
                          {selected.confidence_band
                            ?? "Not evaluated"}
                        </dd>
                      </div>


                      <div className="flex justify-between gap-4">
                        <dt className="text-slate-500">
                          Restricted
                        </dt>

                        <dd className="font-medium text-slate-900">
                          {selected.restricted_action
                            ? "Yes"
                            : "No"}
                        </dd>
                      </div>

                    </dl>
                  </div>


                  <div className="border-t border-slate-200 pt-6">

                    <h3 className="text-sm font-semibold text-slate-900">
                      Order context
                    </h3>

                    {selected.orders.length === 0
                      ? (
                        <p className="mt-3 text-sm leading-6 text-slate-500">
                          No verified order context is attached yet.
                        </p>
                      )
                      : (
                        <div className="mt-3 space-y-3">
                          {selected.orders.map(
                            (order) => (
                              <div
                                key={order.external_order_id}
                                className="rounded-xl bg-slate-50 p-3 text-sm"
                              >
                                <p className="font-semibold text-slate-900">
                                  {order.external_order_id}
                                </p>

                                <p className="mt-1 text-slate-500">
                                  {order.status}
                                </p>
                              </div>
                            ),
                          )}
                        </div>
                      )}
                  </div>


                  <div className="border-t border-slate-200 pt-6">

                    <h3 className="text-sm font-semibold text-slate-900">
                      Audit
                    </h3>

                    <p className="mt-2 text-sm text-slate-500">
                      {selected.audit_events.length} recorded events
                    </p>

                  </div>

                </aside>

              </div>

            </div>
          )}

        </section>

      </div>

    </main>
  );
}