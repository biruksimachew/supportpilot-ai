"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  getAgentQueue,
  StaffApiError,
} from "@/lib/staff-api";

import {
  getSupabaseBrowserClient,
} from "@/lib/supabase-browser";

import type {
  AgentQueueItem,
  ConfidenceBand,
  TicketChannel,
  TicketPriority,
  TicketStatus,
} from "@/lib/staff-types";

import StaffShell
  from "@/components/staff-shell";


const STATUS_OPTIONS:
  {
    value: TicketStatus;
    label: string;
  }[] = [
    { value: "NEW", label: "New" },
    { value: "TRIAGED", label: "Triaged" },
    { value: "DRAFTED", label: "Drafted" },
    { value: "AUTO_RESPONDED", label: "Auto responded" },
    { value: "REVIEW_REQUIRED", label: "Review required" },
    { value: "WAITING_CUSTOMER", label: "Waiting customer" },
    { value: "FAILED", label: "Failed" },
    { value: "RESOLVED", label: "Resolved" },
  ];


const INTENT_OPTIONS = [
  { value: "order_status", label: "Order status" },
  { value: "shipping", label: "Shipping" },
  { value: "return", label: "Return" },
  { value: "damaged_item", label: "Damaged item" },
  { value: "product", label: "Product" },
  { value: "account", label: "Account" },
  { value: "complaint", label: "Complaint" },
  { value: "other", label: "Other" },
];


function humanize(
  value: string | null,
): string {
  if (!value) {
    return "-";
  }

  return value
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(
      /\b\w/g,
      (character) =>
        character.toUpperCase(),
    );
}


function formatRelativeTime(
  value: string | null,
): string {
  if (!value) {
    return "No activity";
  }

  const timestamp =
    new Date(value);

  if (
    Number.isNaN(
      timestamp.getTime(),
    )
  ) {
    return "Unknown time";
  }

  const difference =
    timestamp.getTime()
    - Date.now();

  const absolute =
    Math.abs(difference);

  const formatter =
    new Intl.RelativeTimeFormat(
      undefined,
      {
        numeric:
          "auto",
      },
    );

  const minute =
    60 * 1000;

  const hour =
    60 * minute;

  const day =
    24 * hour;

  if (absolute < minute) {
    return "just now";
  }

  if (absolute < hour) {
    return formatter.format(
      Math.round(
        difference / minute,
      ),
      "minute",
    );
  }

  if (absolute < day) {
    return formatter.format(
      Math.round(
        difference / hour,
      ),
      "hour",
    );
  }

  return formatter.format(
    Math.round(
      difference / day,
    ),
    "day",
  );
}


function statusClasses(
  status: TicketStatus,
): string {
  switch (status) {
    case "REVIEW_REQUIRED":
      return (
        "border-amber-200 "
        + "bg-amber-50 "
        + "text-amber-800"
      );

    case "FAILED":
      return (
        "border-red-200 "
        + "bg-red-50 "
        + "text-red-700"
      );

    case "WAITING_CUSTOMER":
      return (
        "border-blue-200 "
        + "bg-blue-50 "
        + "text-blue-700"
      );

    case "AUTO_RESPONDED":
      return (
        "border-emerald-200 "
        + "bg-emerald-50 "
        + "text-emerald-700"
      );

    case "DRAFTED":
      return (
        "border-violet-200 "
        + "bg-violet-50 "
        + "text-violet-700"
      );

    case "RESOLVED":
      return (
        "border-slate-200 "
        + "bg-slate-100 "
        + "text-slate-600"
      );

    default:
      return (
        "border-slate-200 "
        + "bg-white "
        + "text-slate-700"
      );
  }
}


function priorityClasses(
  priority: TicketPriority,
): string {
  switch (priority) {
    case "P1":
      return (
        "bg-red-100 "
        + "text-red-800"
      );

    case "P2":
      return (
        "bg-orange-100 "
        + "text-orange-800"
      );

    case "P3":
      return (
        "bg-slate-100 "
        + "text-slate-700"
      );

    case "P4":
      return (
        "bg-slate-50 "
        + "text-slate-500"
      );
  }
}


function confidenceClasses(
  band:
    ConfidenceBand | null,
): string {
  switch (band) {
    case "HIGH":
      return (
        "bg-emerald-50 "
        + "text-emerald-700"
      );

    case "MEDIUM":
      return (
        "bg-amber-50 "
        + "text-amber-700"
      );

    case "LOW":
      return (
        "bg-red-50 "
        + "text-red-700"
      );

    default:
      return (
        "bg-slate-100 "
        + "text-slate-500"
      );
  }
}


export default function AgentConsole() {
  const router =
    useRouter();

  const [
    accessToken,
    setAccessToken,
  ] =
    useState<
      string | null
    >(null);

  const [
    staffEmail,
    setStaffEmail,
  ] =
    useState("");

  const [
    tickets,
    setTickets,
  ] =
    useState<
      AgentQueueItem[]
    >([]);

  const [
    total,
    setTotal,
  ] =
    useState(0);

  const [
    statusFilter,
    setStatusFilter,
  ] =
    useState<
      TicketStatus | ""
    >("");

  const [
    priorityFilter,
    setPriorityFilter,
  ] =
    useState<
      TicketPriority | ""
    >("");

  const [
    channelFilter,
    setChannelFilter,
  ] =
    useState<
      TicketChannel | ""
    >("");

  const [
    intentFilter,
    setIntentFilter,
  ] =
    useState("");

  const [
    includeResolved,
    setIncludeResolved,
  ] =
    useState(false);

  const [
    authLoading,
    setAuthLoading,
  ] =
    useState(true);

  const [
    queueLoading,
    setQueueLoading,
  ] =
    useState(true);

  const [
    error,
    setError,
  ] =
    useState<
      string | null
    >(null);


  const reviewInView =
    useMemo(
      () =>
        tickets.filter(
          (ticket) =>
            ticket.status
            === "REVIEW_REQUIRED",
        ).length,
      [
        tickets,
      ],
    );


  const urgentInView =
    useMemo(
      () =>
        tickets.filter(
          (ticket) =>
            ticket.priority
              === "P1"
            ||
            ticket.priority
              === "P2",
        ).length,
      [
        tickets,
      ],
    );


  const unassignedInView =
    useMemo(
      () =>
        tickets.filter(
          (ticket) =>
            !ticket.assignee_name,
        ).length,
      [
        tickets,
      ],
    );


  const handleAuthFailure =
    useCallback(
      async () => {
        const supabase =
          getSupabaseBrowserClient();

        await supabase.auth
          .signOut();

        setAccessToken(
          null,
        );

        router.replace(
          "/staff/login",
        );
      },
      [
        router,
      ],
    );


  useEffect(() => {
    let active =
      true;

    const supabase =
      getSupabaseBrowserClient();

    async function initializeAuth() {
      try {
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
          sessionError
          ||
          !data.session
        ) {
          router.replace(
            "/staff/login",
          );
          return;
        }

        setAccessToken(
          data.session
            .access_token,
        );

        setStaffEmail(
          data.session
            .user
            .email
          ?? "",
        );
      } finally {
        if (active) {
          setAuthLoading(
            false,
          );
        }
      }
    }

    const {
      data: {
        subscription,
      },
    } =
      supabase.auth
        .onAuthStateChange(
          (
            _event,
            session,
          ) => {
            if (!active) {
              return;
            }

            if (!session) {
              setAccessToken(
                null,
              );

              router.replace(
                "/staff/login",
              );
              return;
            }

            setAccessToken(
              session
                .access_token,
            );

            setStaffEmail(
              session
                .user
                .email
              ?? "",
            );
          },
        );

    void initializeAuth();

    return () => {
      active = false;

      subscription
        .unsubscribe();
    };
  }, [
    router,
  ]);


  const fetchQueue =
    useCallback(
      async () => {
        if (!accessToken) {
          return null;
        }

        return getAgentQueue(
          accessToken,
          {
            status:
              statusFilter
              || undefined,
            priority:
              priorityFilter
              || undefined,
            intent:
              intentFilter
              || undefined,
            channel:
              channelFilter
              || undefined,
            includeResolved,
            limit:
              100,
            offset:
              0,
          },
        );
      },
      [
        accessToken,
        channelFilter,
        includeResolved,
        intentFilter,
        priorityFilter,
        statusFilter,
      ],
    );


  const refreshQueue =
    useCallback(
      async () => {
        const result =
          await fetchQueue();

        if (!result) {
          return;
        }

        setTickets(
          result.items,
        );

        setTotal(
          result.total,
        );

        setError(
          null,
        );
      },
      [
        fetchQueue,
      ],
    );


  useEffect(() => {
    if (
      authLoading
      ||
      !accessToken
    ) {
      return;
    }

    let cancelled =
      false;

    void fetchQueue()
      .then(
        (result) => {
          if (
            cancelled
            ||
            !result
          ) {
            return;
          }

          setTickets(
            result.items,
          );

          setTotal(
            result.total,
          );

          setError(
            null,
          );
        },
      )
      .catch(
        (caught) => {
          if (cancelled) {
            return;
          }

          if (
            caught
              instanceof StaffApiError
            &&
            (
              caught.status
                === 401
              ||
              caught.status
                === 403
            )
          ) {
            void handleAuthFailure();
            return;
          }

          setError(
            "The support queue could not be loaded.",
          );
        },
      )
      .finally(
        () => {
          if (!cancelled) {
            setQueueLoading(
              false,
            );
          }
        },
      );

    return () => {
      cancelled = true;
    };
  }, [
    accessToken,
    authLoading,
    fetchQueue,
    handleAuthFailure,
  ]);


  async function handleRefresh() {
    setQueueLoading(
      true,
    );

    try {
      await refreshQueue();
    } catch (caught) {
      if (
        caught
          instanceof StaffApiError
        &&
        (
          caught.status
            === 401
          ||
          caught.status
            === 403
        )
      ) {
        await handleAuthFailure();
        return;
      }

      setError(
        "The support queue could not be refreshed.",
      );
    } finally {
      setQueueLoading(
        false,
      );
    }
  }


  function clearFilters() {
    setStatusFilter("");
    setPriorityFilter("");
    setChannelFilter("");
    setIntentFilter("");
    setIncludeResolved(false);
  }


  if (authLoading) {
    return (
      <div
        className={
          "flex min-h-screen "
          + "items-center "
          + "justify-center "
          + "bg-slate-100 "
          + "text-sm "
          + "text-slate-500"
        }
      >
        Loading support queue...
      </div>
    );
  }


  return (
    <StaffShell
      active="queue"
      title="Support queue"
      subtitle={
        (
          total
          + " matching tickets · "
          + reviewInView
          + " need review · "
          + urgentInView
          + " high priority"
        )
      }
      staffEmail={
        staffEmail
      }
      onRefresh={
        () =>
          void handleRefresh()
      }
      refreshBusy={
        queueLoading
      }
    >
      <div
        className={
          "mx-auto max-w-[1500px] "
          + "space-y-4 "
          + "p-4 "
          + "sm:p-5 "
          + "xl:p-6"
        }
      >
        {error && (
          <div
            role="alert"
            className={
              "rounded-xl "
              + "border border-red-200 "
              + "bg-red-50 "
              + "px-4 py-3 "
              + "text-sm "
              + "text-red-800"
            }
          >
            {error}
          </div>
        )}

        <section
          className={
            "rounded-2xl "
            + "border "
            + "border-slate-200 "
            + "bg-white "
            + "p-4 "
            + "shadow-sm"
          }
        >
          <div
            className={
              "flex flex-wrap "
              + "items-center "
              + "justify-between "
              + "gap-4"
            }
          >
            <div>
              <p
                className={
                  "text-[10px] "
                  + "font-bold "
                  + "uppercase "
                  + "tracking-[0.16em] "
                  + "text-slate-400"
                }
              >
                Live work
              </p>

              <h2
                className={
                  "mt-1 text-lg "
                  + "font-semibold"
                }
              >
                Tickets
              </h2>
            </div>

            <div
              className={
                "grid grid-cols-3 "
                + "gap-2"
              }
            >
              <div
                className={
                  "rounded-xl "
                  + "bg-slate-50 "
                  + "px-3 py-2 "
                  + "text-center"
                }
              >
                <p
                  className={
                    "text-lg "
                    + "font-semibold"
                  }
                >
                  {reviewInView}
                </p>

                <p
                  className={
                    "text-[9px] "
                    + "uppercase "
                    + "tracking-wide "
                    + "text-slate-400"
                  }
                >
                  Review
                </p>
              </div>

              <div
                className={
                  "rounded-xl "
                  + "bg-slate-50 "
                  + "px-3 py-2 "
                  + "text-center"
                }
              >
                <p
                  className={
                    "text-lg "
                    + "font-semibold"
                  }
                >
                  {urgentInView}
                </p>

                <p
                  className={
                    "text-[9px] "
                    + "uppercase "
                    + "tracking-wide "
                    + "text-slate-400"
                  }
                >
                  P1/P2
                </p>
              </div>

              <div
                className={
                  "rounded-xl "
                  + "bg-slate-50 "
                  + "px-3 py-2 "
                  + "text-center"
                }
              >
                <p
                  className={
                    "text-lg "
                    + "font-semibold"
                  }
                >
                  {unassignedInView}
                </p>

                <p
                  className={
                    "text-[9px] "
                    + "uppercase "
                    + "tracking-wide "
                    + "text-slate-400"
                  }
                >
                  Unassigned
                </p>
              </div>
            </div>
          </div>

          <div
            className={
              "mt-4 grid "
              + "gap-2 "
              + "sm:grid-cols-2 "
              + "xl:grid-cols-4"
            }
          >
            <select
              aria-label={
                "Ticket status"
              }
              value={
                statusFilter
              }
              onChange={
                (event) => {
                  const value =
                    event
                      .target
                      .value as
                      TicketStatus | "";

                  setStatusFilter(
                    value,
                  );

                  if (
                    value
                    === "RESOLVED"
                  ) {
                    setIncludeResolved(
                      true,
                    );
                  }
                }
              }
              className={
                "rounded-xl "
                + "border "
                + "border-slate-200 "
                + "bg-white "
                + "px-3 py-2.5 "
                + "text-xs "
                + "text-slate-700 "
                + "outline-none "
                + "focus:border-slate-400"
              }
            >
              <option value="">
                All statuses
              </option>

              {STATUS_OPTIONS.map(
                (option) => (
                  <option
                    key={
                      option.value
                    }
                    value={
                      option.value
                    }
                  >
                    {option.label}
                  </option>
                ),
              )}
            </select>

            <select
              aria-label={
                "Ticket priority"
              }
              value={
                priorityFilter
              }
              onChange={
                (event) =>
                  setPriorityFilter(
                    event
                      .target
                      .value as
                      TicketPriority | "",
                  )
              }
              className={
                "rounded-xl "
                + "border "
                + "border-slate-200 "
                + "bg-white "
                + "px-3 py-2.5 "
                + "text-xs "
                + "text-slate-700 "
                + "outline-none "
                + "focus:border-slate-400"
              }
            >
              <option value="">
                All priorities
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
              aria-label={
                "Ticket intent"
              }
              value={
                intentFilter
              }
              onChange={
                (event) =>
                  setIntentFilter(
                    event
                      .target
                      .value,
                  )
              }
              className={
                "rounded-xl "
                + "border "
                + "border-slate-200 "
                + "bg-white "
                + "px-3 py-2.5 "
                + "text-xs "
                + "text-slate-700 "
                + "outline-none "
                + "focus:border-slate-400"
              }
            >
              <option value="">
                All intents
              </option>

              {INTENT_OPTIONS.map(
                (option) => (
                  <option
                    key={
                      option.value
                    }
                    value={
                      option.value
                    }
                  >
                    {option.label}
                  </option>
                ),
              )}
            </select>

            <select
              aria-label={
                "Ticket channel"
              }
              value={
                channelFilter
              }
              onChange={
                (event) =>
                  setChannelFilter(
                    event
                      .target
                      .value as
                      TicketChannel | "",
                  )
              }
              className={
                "rounded-xl "
                + "border "
                + "border-slate-200 "
                + "bg-white "
                + "px-3 py-2.5 "
                + "text-xs "
                + "text-slate-700 "
                + "outline-none "
                + "focus:border-slate-400"
              }
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

          <div
            className={
              "mt-3 flex "
              + "items-center "
              + "justify-between "
              + "gap-3"
            }
          >
            <label
              className={
                "flex cursor-pointer "
                + "items-center "
                + "gap-2 "
                + "text-xs "
                + "text-slate-600"
              }
            >
              <input
                type="checkbox"
                checked={
                  includeResolved
                }
                onChange={
                  (event) => {
                    const checked =
                      event
                        .target
                        .checked;

                    setIncludeResolved(
                      checked,
                    );

                    if (
                      !checked
                      &&
                      statusFilter
                        === "RESOLVED"
                    ) {
                      setStatusFilter("");
                    }
                  }
                }
                className={
                  "h-4 w-4 "
                  + "rounded "
                  + "border-slate-300"
                }
              />

              Include resolved
            </label>

            <button
              type="button"
              onClick={
                clearFilters
              }
              className={
                "text-xs "
                + "font-semibold "
                + "text-slate-500 "
                + "transition "
                + "hover:text-slate-900"
              }
            >
              Reset filters
            </button>
          </div>
        </section>

        <section
          className={
            "overflow-hidden "
            + "rounded-2xl "
            + "border "
            + "border-slate-200 "
            + "bg-white "
            + "shadow-sm"
          }
        >
          <div
            className={
              "grid "
              + "border-b "
              + "border-slate-200 "
              + "bg-slate-50 "
              + "px-4 py-3 "
              + "text-[10px] "
              + "font-bold "
              + "uppercase "
              + "tracking-[0.12em] "
              + "text-slate-400 "
              + "lg:grid-cols-"
              + "[minmax(0,1.6fr)_150px_130px_130px]"
            }
          >
            <span>
              Ticket
            </span>

            <span
              className={
                "hidden lg:block"
              }
            >
              Customer
            </span>

            <span
              className={
                "hidden lg:block"
              }
            >
              Assignee
            </span>

            <span
              className={
                "hidden lg:block "
                + "text-right"
              }
            >
              Updated
            </span>
          </div>

          {queueLoading && (
            <div
              className={
                "px-5 py-4 "
                + "text-sm "
                + "text-slate-400"
              }
            >
              Refreshing queue...
            </div>
          )}

          {
            !queueLoading
            &&
            tickets.length
              === 0
            &&
            (
              <div
                className={
                  "px-8 py-16 "
                  + "text-center"
                }
              >
                <p
                  className={
                    "font-semibold "
                    + "text-slate-800"
                  }
                >
                  Queue is clear
                </p>

                <p
                  className={
                    "mt-2 text-sm "
                    + "text-slate-500"
                  }
                >
                  No tickets match the
                  current filters.
                </p>
              </div>
            )
          }

          <div
            className={
              "divide-y "
              + "divide-slate-100"
            }
          >
            {tickets.map(
              (ticket) => (
                <button
                  key={
                    ticket.id
                  }
                  type="button"
                  onClick={
                    () =>
                      router.push(
                        (
                          "/staff/tickets/"
                          + ticket.id
                        ),
                      )
                  }
                  className={
                    "grid w-full "
                    + "gap-3 "
                    + "px-4 py-4 "
                    + "text-left "
                    + "transition "
                    + "hover:bg-slate-50 "
                    + "lg:grid-cols-"
                    + "[minmax(0,1.6fr)_150px_130px_130px] "
                    + "lg:items-center"
                  }
                >
                  <div
                    className={
                      "min-w-0"
                    }
                  >
                    <div
                      className={
                        "flex flex-wrap "
                        + "items-center "
                        + "gap-2"
                      }
                    >
                      <p
                        className={
                          "text-sm "
                          + "font-semibold "
                          + "text-slate-950"
                        }
                      >
                        {ticket.reference}
                      </p>

                      <span
                        className={[
                          (
                            "rounded-full "
                            + "border "
                            + "px-2 py-0.5 "
                            + "text-[9px] "
                            + "font-semibold"
                          ),
                          statusClasses(
                            ticket.status,
                          ),
                        ].join(" ")}
                      >
                        {
                          humanize(
                            ticket.status,
                          )
                        }
                      </span>

                      <span
                        className={[
                          (
                            "rounded-md "
                            + "px-2 py-0.5 "
                            + "text-[9px] "
                            + "font-bold"
                          ),
                          priorityClasses(
                            ticket.priority,
                          ),
                        ].join(" ")}
                      >
                        {ticket.priority}
                      </span>
                    </div>

                    <p
                      className={
                        "mt-2 "
                        + "line-clamp-1 "
                        + "text-sm "
                        + "text-slate-600"
                      }
                    >
                      {
                        ticket.last_message_body
                        ?? "No messages yet."
                      }
                    </p>

                    <div
                      className={
                        "mt-2 flex "
                        + "flex-wrap "
                        + "items-center "
                        + "gap-2 "
                        + "text-[10px] "
                        + "text-slate-400"
                      }
                    >
                      <span>
                        {
                          humanize(
                            ticket.channel,
                          )
                        }
                      </span>

                      <span>
                        ·
                      </span>

                      <span>
                        {
                          humanize(
                            ticket.intent,
                          )
                        }
                      </span>

                      <span>
                        ·
                      </span>

                      <span
                        className={[
                          (
                            "rounded-full "
                            + "px-2 py-0.5 "
                            + "font-semibold"
                          ),
                          confidenceClasses(
                            ticket
                              .confidence_band,
                          ),
                        ].join(" ")}
                      >
                        {
                          ticket
                            .confidence_band
                          ?? "NOT EVALUATED"
                        }
                      </span>
                    </div>
                  </div>

                  <div
                    className={
                      "min-w-0 "
                      + "lg:block"
                    }
                  >
                    <p
                      className={
                        "truncate "
                        + "text-xs "
                        + "font-medium "
                        + "text-slate-700"
                      }
                    >
                      {
                        ticket.customer_name
                        ?? "Unverified customer"
                      }
                    </p>

                    <p
                      className={
                        "mt-0.5 "
                        + "truncate "
                        + "text-[10px] "
                        + "text-slate-400"
                      }
                    >
                      {
                        ticket.customer_email
                        ?? "No verified email"
                      }
                    </p>
                  </div>

                  <p
                    className={
                      "truncate "
                      + "text-xs "
                      + "text-slate-500"
                    }
                  >
                    {
                      ticket.assignee_name
                      ?? "Unassigned"
                    }
                  </p>

                  <div
                    className={
                      "flex items-center "
                      + "justify-between "
                      + "gap-3 "
                      + "lg:justify-end"
                    }
                  >
                    <span
                      className={
                        "text-xs "
                        + "text-slate-400"
                      }
                    >
                      {
                        formatRelativeTime(
                          ticket.last_message_at
                          ?? ticket.updated_at,
                        )
                      }
                    </span>

                    <span
                      aria-hidden="true"
                      className={
                        "text-lg "
                        + "text-slate-300"
                      }
                    >
                      →
                    </span>
                  </div>
                </button>
              ),
            )}
          </div>
        </section>
      </div>
    </StaffShell>
  );
}
