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
  ConfidenceBand,
  TicketChannel,
  TicketPriority,
  TicketStatus,
} from "@/lib/staff-types";


const STATUS_OPTIONS:
  {
    value: TicketStatus;
    label: string;
  }[] = [

    {
      value:
        "NEW",
      label:
        "New",
    },

    {
      value:
        "TRIAGED",
      label:
        "Triaged",
    },

    {
      value:
        "DRAFTED",
      label:
        "Drafted",
    },

    {
      value:
        "AUTO_RESPONDED",
      label:
        "Auto responded",
    },

    {
      value:
        "REVIEW_REQUIRED",
      label:
        "Review required",
    },

    {
      value:
        "WAITING_CUSTOMER",
      label:
        "Waiting customer",
    },

    {
      value:
        "FAILED",
      label:
        "Failed",
    },

    {
      value:
        "RESOLVED",
      label:
        "Resolved",
    },
  ];


const INTENT_OPTIONS = [
  {
    value:
      "order_status",
    label:
      "Order status",
  },

  {
    value:
      "shipping",
    label:
      "Shipping",
  },

  {
    value:
      "return",
    label:
      "Return",
  },

  {
    value:
      "damaged_item",
    label:
      "Damaged item",
  },

  {
    value:
      "product",
    label:
      "Product",
  },

  {
    value:
      "account",
    label:
      "Account",
  },

  {
    value:
      "complaint",
    label:
      "Complaint",
  },

  {
    value:
      "other",
    label:
      "Other",
  },
];


function humanize(
  value: string | null,
): string {

  if (!value) {
    return "-";
  }


  const words =
    value
      .replaceAll(
        "_",
        " ",
      )
      .toLowerCase();


  return (
    words
      .charAt(
        0,
      )
      .toUpperCase()
    + words.slice(
      1,
    )
  );
}


function formatRelativeTime(
  value: string | null,
): string {

  if (!value) {
    return "No activity";
  }


  const timestamp =
    new Date(
      value,
    );


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
    Math.abs(
      difference,
    );


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


  if (
    absolute
    < minute
  ) {
    return "just now";
  }


  if (
    absolute
    < hour
  ) {
    return formatter.format(
      Math.round(
        difference
        / minute,
      ),
      "minute",
    );
  }


  if (
    absolute
    < day
  ) {
    return formatter.format(
      Math.round(
        difference
        / hour,
      ),
      "hour",
    );
  }


  return formatter.format(
    Math.round(
      difference
      / day,
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


    case "RESOLVED":
      return (
        "border-slate-200 "
        + "bg-slate-100 "
        + "text-slate-600"
      );


    case "DRAFTED":
      return (
        "border-violet-200 "
        + "bg-violet-50 "
        + "text-violet-700"
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
    >(
      null,
    );


  const [
    staffEmail,
    setStaffEmail,
  ] =
    useState(
      "",
    );


  const [
    tickets,
    setTickets,
  ] =
    useState<
      AgentQueueItem[]
    >(
      [],
    );


  const [
    total,
    setTotal,
  ] =
    useState(
      0,
    );


  const [
    selected,
    setSelected,
  ] =
    useState<
      AgentTicketDetail | null
    >(
      null,
    );


  const [
    selectedId,
    setSelectedId,
  ] =
    useState<
      string | null
    >(
      null,
    );


  const [
    statusFilter,
    setStatusFilter,
  ] =
    useState<
      TicketStatus | ""
    >(
      "",
    );


  const [
    priorityFilter,
    setPriorityFilter,
  ] =
    useState<
      TicketPriority | ""
    >(
      "",
    );


  const [
    channelFilter,
    setChannelFilter,
  ] =
    useState<
      TicketChannel | ""
    >(
      "",
    );


  const [
    intentFilter,
    setIntentFilter,
  ] =
    useState(
      "",
    );


  const [
    includeResolved,
    setIncludeResolved,
  ] =
    useState(
      false,
    );


  const [
    authLoading,
    setAuthLoading,
  ] =
    useState(
      true,
    );


  const [
    queueLoading,
    setQueueLoading,
  ] =
    useState(
      true,
    );

  const [
    detailLoading,
    setDetailLoading,
  ] =
    useState(
      false,
    );


  const [
    error,
    setError,
  ] =
    useState<
      string | null
    >(
      null,
    );


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

            || ticket.priority
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
            (
              "The support queue "
              + "could not be loaded."
            ),
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


  async function openTicket(
    ticketId: string,
  ) {

    if (!accessToken) {
      return;
    }


    setSelectedId(
      ticketId,
    );


    setDetailLoading(
      true,
    );


    setError(
      null,
    );


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
        (
          "The ticket workspace "
          + "could not be loaded."
        ),
      );

    } finally {

      setDetailLoading(
        false,
      );
    }
  }


  async function refreshWorkspace() {

    if (!accessToken) {
      return;
    }


    setQueueLoading(
    
      true,
    );


    setError(
      null,
    );


    try {

      const result =
        await fetchQueue();


      if (result) {

        setTickets(
          result.items,
        );


        setTotal(
          result.total,
        );
      }


      if (selectedId) {

        await openTicket(
          selectedId,
        );
      }

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
        (
          "The support workspace "
          + "could not be refreshed."
        ),
      );

    } finally {

      setQueueLoading(
        false,
      );
    }
  }


  function clearFilters() {

    setStatusFilter(
      "",
    );

    setPriorityFilter(
      "",
    );

    setChannelFilter(
      "",
    );

    setIntentFilter(
      "",
    );

    setIncludeResolved(
      false,
    );
  }


  async function logout() {

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
  }


  if (authLoading) {

    return (
      <div
        className={
          "flex min-h-screen "
          + "items-center justify-center "
          + "bg-slate-50 "
          + "text-sm text-slate-500"
        }
      >
        Loading staff console...
      </div>
    );
  }


  return (
    <main
      className={
        "min-h-screen "
        + "bg-slate-50 "
        + "text-slate-950"
      }
    >

      <header
        className={
          "border-b "
          + "border-slate-200 "
          + "bg-white"
        }
      >

        <div
          className={
            "mx-auto flex "
            + "max-w-[1600px] "
            + "items-center "
            + "justify-between "
            + "gap-5 "
            + "px-5 py-4 "
            + "lg:px-7"
          }
        >

          <div
            className={
              "flex items-center "
              + "gap-3"
            }
          >

            <div
              className={
                "flex h-10 w-10 "
                + "items-center "
                + "justify-center "
                + "rounded-xl "
                + "bg-slate-950 "
                + "text-sm font-bold "
                + "text-white"
              }
            >
              SP
            </div>


            <div>

              <p
                className={
                  "text-[11px] "
                  + "font-semibold "
                  + "uppercase "
                  + "tracking-[0.18em] "
                  + "text-slate-400"
                }
              >
                SupportPilot AI
              </p>


              <h1
                className={
                  "mt-0.5 "
                  + "text-lg "
                  + "font-semibold "
                  + "tracking-tight "
                  + "text-slate-950"
                }
              >
                Agent Console
              </h1>

            </div>

          </div>


          <div
            className={
              "flex items-center "
              + "gap-3"
            }
          >

            <button
              type="button"

              disabled={
                queueLoading
                || detailLoading
              }

              onClick={
                () =>
                  void refreshWorkspace()
              }

              className={
                "hidden rounded-xl "
                + "border border-slate-200 "
                + "bg-white "
                + "px-4 py-2 "
                + "text-sm font-medium "
                + "text-slate-700 "
                + "transition "
                + "hover:bg-slate-50 "
                + "disabled:opacity-50 "
                + "sm:block"
              }
            >
              {
                queueLoading
                  ? "Refreshing..."
                  : "Refresh"
              }
            </button>


            <div
              className={
                "hidden text-right "
                + "sm:block"
              }
            >

              <p
                className={
                  "text-xs font-medium "
                  + "text-slate-900"
                }
              >
                Authenticated staff
              </p>


              <p
                className={
                  "mt-0.5 "
                  + "max-w-65 "
                  + "truncate "
                  + "text-xs "
                  + "text-slate-500"
                }
              >
                {staffEmail}
              </p>

            </div>


            <button
              type="button"

              onClick={
                () =>
                  void logout()
              }

              className={
                "rounded-xl "
                + "border border-slate-200 "
                + "bg-white "
                + "px-4 py-2 "
                + "text-sm font-medium "
                + "text-slate-700 "
                + "transition "
                + "hover:bg-slate-50"
              }
            >
              Sign out
            </button>

          </div>

        </div>

      </header>


      {error && (
        <div
          className={
            "mx-auto "
            + "max-w-[1600px] "
            + "px-5 pt-5 "
            + "lg:px-7"
          }
        >

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

        </div>
      )}


      <div
        className={
          "mx-auto grid "
          + "max-w-[1600px] "
          + "gap-5 "
          + "p-5 "
          + "lg:grid-cols-"
          + "[420px_minmax(0,1fr)] "
          + "lg:px-7"
        }
      >

        <section
          className={
            "overflow-hidden "
            + "rounded-2xl "
            + "border border-slate-200 "
            + "bg-white "
            + "shadow-sm"
          }
        >

          <div
            className={
              "border-b "
              + "border-slate-200 "
              + "p-4"
            }
          >

            <div
              className={
                "flex items-start "
                + "justify-between "
                + "gap-4"
              }
            >

              <div>

                <p
                  className={
                    "text-xs "
                    + "font-semibold "
                    + "uppercase "
                    + "tracking-[0.15em] "
                    + "text-slate-400"
                  }
                >
                  Operations
                </p>


                <h2
                  className={
                    "mt-1 "
                    + "text-lg "
                    + "font-semibold "
                    + "text-slate-950"
                  }
                >
                  Support queue
                </h2>

              </div>


              <div
                className={
                  "rounded-xl "
                  + "bg-slate-100 "
                  + "px-3 py-2 "
                  + "text-right"
                }
              >

                <p
                  className={
                    "text-lg "
                    + "font-semibold "
                    + "leading-none "
                    + "text-slate-950"
                  }
                >
                  {total}
                </p>


                <p
                  className={
                    "mt-1 "
                    + "text-[10px] "
                    + "font-medium "
                    + "uppercase "
                    + "tracking-wide "
                    + "text-slate-500"
                  }
                >
                  Matching
                </p>

              </div>

            </div>


            <div
              className={
                "mt-4 grid "
                + "grid-cols-3 gap-2"
              }
            >

              <div
                className={
                  "rounded-xl "
                  + "border border-slate-200 "
                  + "bg-slate-50 "
                  + "p-3"
                }
              >

                <p
                  className={
                    "text-lg "
                    + "font-semibold "
                    + "text-slate-950"
                  }
                >
                  {reviewInView}
                </p>

                <p
                  className={
                    "mt-0.5 "
                    + "text-[10px] "
                    + "uppercase "
                    + "tracking-wide "
                    + "text-slate-500"
                  }
                >
                  Review in view
                </p>

              </div>


              <div
                className={
                  "rounded-xl "
                  + "border border-slate-200 "
                  + "bg-slate-50 "
                  + "p-3"
                }
              >

                <p
                  className={
                    "text-lg "
                    + "font-semibold "
                    + "text-slate-950"
                  }
                >
                  {urgentInView}
                </p>

                <p
                  className={
                    "mt-0.5 "
                    + "text-[10px] "
                    + "uppercase "
                    + "tracking-wide "
                    + "text-slate-500"
                  }
                >
                  P1/P2 in view
                </p>

              </div>


              <div
                className={
                  "rounded-xl "
                  + "border border-slate-200 "
                  + "bg-slate-50 "
                  + "p-3"
                }
              >

                <p
                  className={
                    "text-lg "
                    + "font-semibold "
                    + "text-slate-950"
                  }
                >
                  {unassignedInView}
                </p>

                <p
                  className={
                    "mt-0.5 "
                    + "text-[10px] "
                    + "uppercase "
                    + "tracking-wide "
                    + "text-slate-500"
                  }
                >
                  Unassigned
                </p>

              </div>

            </div>


            <div
              className={
                "mt-4 grid "
                + "grid-cols-2 gap-2"
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
                        TicketStatus
                        | "";


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
                  + "border border-slate-200 "
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

                {
                  STATUS_OPTIONS.map(
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
                  )
                }

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
                        TicketPriority
                        | "",
                    )
                }

                className={
                  "rounded-xl "
                  + "border border-slate-200 "
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
                  + "border border-slate-200 "
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

                {
                  INTENT_OPTIONS.map(
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
                  )
                }

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
                        TicketChannel
                        | "",
                    )
                }

                className={
                  "rounded-xl "
                  + "border border-slate-200 "
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
                        setStatusFilter(
                          "",
                        );
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
                  + "font-medium "
                  + "text-slate-500 "
                  + "transition "
                  + "hover:text-slate-900"
                }
              >
                Clear filters
              </button>

            </div>

          </div>


          <div
            className={
              "max-h-[calc(100vh-310px)] "
              + "min-h-105 "
              + "overflow-y-auto"
            }
          >

            {queueLoading && (
              <div
                className={
                  "border-b "
                  + "border-slate-100 "
                  + "px-4 py-3 "
                  + "text-xs "
                  + "text-slate-400"
                }
              >
                Refreshing queue...
              </div>
            )}


            {
              !queueLoading
              &&
              tickets.length === 0
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
                      "font-medium "
                      + "text-slate-800"
                    }
                  >
                    Queue is clear
                  </p>


                  <p
                    className={
                      "mt-2 "
                      + "text-sm "
                      + "leading-6 "
                      + "text-slate-500"
                    }
                  >
                    No tickets match the
                    current filters.
                  </p>

                </div>
              )
            }


            {
              tickets.map(
                (ticket) => {

                  const active =
                    ticket.id
                    === selectedId;


                  return (
                    <button
                      type="button"

                      key={
                        ticket.id
                      }

                      aria-pressed={
                        active
                      }

                      onClick={
                        () =>
                          void openTicket(
                            ticket.id,
                          )
                      }

                      className={[
                        (
                          "block w-full "
                          + "border-b "
                          + "border-slate-100 "
                          + "p-4 text-left "
                          + "transition"
                        ),

                        active
                          ? (
                            "bg-slate-950 "
                            + "text-white"
                          )
                          : (
                            "bg-white "
                            + "hover:bg-slate-50"
                          ),
                      ].join(
                        " ",
                      )}
                    >

                      <div
                        className={
                          "flex "
                          + "items-start "
                          + "justify-between "
                          + "gap-4"
                        }
                      >

                        <div
                          className="min-w-0"
                        >

                          <div
                            className={
                              "flex "
                              + "flex-wrap "
                              + "items-center "
                              + "gap-2"
                            }
                          >

                            <p
                              className={[
                                (
                                  "text-sm "
                                  + "font-semibold"
                                ),

                                active
                                  ? "text-white"
                                  : "text-slate-950",
                              ].join(
                                " ",
                              )}
                            >
                              {ticket.reference}
                            </p>


                            <span
                              className={[
                                (
                                  "rounded-full "
                                  + "border "
                                  + "px-2 py-0.5 "
                                  + "text-[10px] "
                                  + "font-semibold"
                                ),

                                active
                                  ? (
                                    "border-white/20 "
                                    + "bg-white/10 "
                                    + "text-white"
                                  )
                                  : statusClasses(
                                      ticket.status,
                                    ),
                              ].join(
                                " ",
                              )}
                            >
                              {
                                humanize(
                                  ticket.status,
                                )
                              }
                            </span>

                          </div>


                          <p
                            className={[
                              (
                                "mt-1.5 "
                                + "truncate "
                                + "text-xs"
                              ),

                              active
                                ? "text-slate-300"
                                : "text-slate-500",
                            ].join(
                              " ",
                            )}
                          >
                            {
                              ticket.customer_name
                              ?? ticket.customer_email
                              ?? "Unverified customer"
                            }
                          </p>

                        </div>


                        <span
                          className={[
                            (
                              "shrink-0 "
                              + "rounded-lg "
                              + "px-2 py-1 "
                              + "text-[11px] "
                              + "font-bold"
                            ),

                            active
                              ? (
                                "bg-white/10 "
                                + "text-white"
                              )
                              : priorityClasses(
                                  ticket.priority,
                                ),
                          ].join(
                            " ",
                          )}
                        >
                          {ticket.priority}
                        </span>

                      </div>


                      <p
                        className={[
                          (
                            "mt-3 "
                            + "line-clamp-2 "
                            + "text-sm "
                            + "leading-5"
                          ),

                          active
                            ? "text-slate-200"
                            : "text-slate-600",
                        ].join(
                          " ",
                        )}
                      >
                        {
                          ticket.last_message_body
                          ?? "No messages"
                        }
                      </p>


                      <div
                        className={
                          "mt-3 flex "
                          + "flex-wrap "
                          + "items-center "
                          + "gap-2"
                        }
                      >

                        <span
                          className={[
                            (
                              "rounded-full "
                              + "px-2 py-1 "
                              + "text-[10px] "
                              + "font-medium"
                            ),

                            active
                              ? (
                                "bg-white/10 "
                                + "text-slate-200"
                              )
                              : (
                                "bg-slate-100 "
                                + "text-slate-600"
                              ),
                          ].join(
                            " ",
                          )}
                        >
                          {
                            humanize(
                              ticket.intent,
                            )
                          }
                        </span>


                        <span
                          className={[
                            (
                              "rounded-full "
                              + "px-2 py-1 "
                              + "text-[10px] "
                              + "font-medium"
                            ),

                            active
                              ? (
                                "bg-white/10 "
                                + "text-slate-200"
                              )
                              : confidenceClasses(
                                  ticket.confidence_band,
                                ),
                          ].join(
                            " ",
                          )}
                        >
                          {
                            ticket.confidence_band
                            ?? "NOT EVALUATED"
                          }
                        </span>


                        <span
                          className={[
                            (
                              "ml-auto "
                              + "text-[10px]"
                            ),

                            active
                              ? "text-slate-400"
                              : "text-slate-400",
                          ].join(
                            " ",
                          )}
                        >
                          {
                            formatRelativeTime(
                              ticket.last_message_at
                              ?? ticket.updated_at,
                            )
                          }
                        </span>

                      </div>


                      <div
                        className={[
                          (
                            "mt-3 flex "
                            + "items-center "
                            + "justify-between "
                            + "gap-3 "
                            + "border-t "
                            + "pt-3 "
                            + "text-[10px]"
                          ),

                          active
                            ? (
                              "border-white/10 "
                              + "text-slate-400"
                            )
                            : (
                              "border-slate-100 "
                              + "text-slate-400"
                            ),
                        ].join(
                          " ",
                        )}
                      >

                        <span>
                          {
                            humanize(
                              ticket.channel,
                            )
                          }
                          {" / "}
                          {
                            ticket.message_count
                          }
                          {
                            ticket.message_count
                              === 1
                              ? " message"
                              : " messages"
                          }
                        </span>


                        <span
                          className="truncate"
                        >
                          {
                            ticket.assignee_name
                            ?? "Unassigned"
                          }
                        </span>

                      </div>

                    </button>
                  );
                },
              )
            }

          </div>

        </section>


        <section
          className={
            "min-h-180 "
            + "overflow-hidden "
            + "rounded-2xl "
            + "border border-slate-200 "
            + "bg-white "
            + "shadow-sm"
          }
        >

          {
            !selected
            &&
            !detailLoading
            &&
            (
              <div
                className={
                  "flex min-h-180 "
                  + "items-center "
                  + "justify-center "
                  + "p-8 "
                  + "text-center"
                }
              >

                <div
                  className="max-w-sm"
                >

                  <div
                    className={
                      "mx-auto flex "
                      + "h-12 w-12 "
                      + "items-center "
                      + "justify-center "
                      + "rounded-2xl "
                      + "bg-slate-100 "
                      + "text-sm "
                      + "font-bold "
                      + "text-slate-600"
                    }
                  >
                    SP
                  </div>


                  <h2
                    className={
                      "mt-5 "
                      + "text-xl "
                      + "font-semibold "
                      + "text-slate-900"
                    }
                  >
                    Select a ticket
                  </h2>


                  <p
                    className={
                      "mt-2 "
                      + "text-sm "
                      + "leading-6 "
                      + "text-slate-500"
                    }
                  >
                    Conversation, customer
                    context, order facts and
                    decision information will
                    appear here.
                  </p>

                </div>

              </div>
            )
          }


          {detailLoading && (
            <div
              className={
                "flex min-h-180 "
                + "items-center "
                + "justify-center "
                + "text-sm "
                + "text-slate-500"
              }
            >
              Loading ticket...
            </div>
          )}


          {
            selected
            &&
            !detailLoading
            &&
            (
              <div>

                <header
                  className={
                    "border-b "
                    + "border-slate-200 "
                    + "p-6"
                  }
                >

                  <div
                    className={
                      "flex flex-wrap "
                      + "items-start "
                      + "justify-between "
                      + "gap-6"
                    }
                  >

                    <div>

                      <div
                        className={
                          "flex flex-wrap "
                          + "items-center "
                          + "gap-2"
                        }
                      >

                        <p
                          className={
                            "text-xs "
                            + "font-semibold "
                            + "uppercase "
                            + "tracking-[0.15em] "
                            + "text-slate-400"
                          }
                        >
                          Ticket
                        </p>


                        <span
                          className={[
                            (
                              "rounded-full "
                              + "border "
                              + "px-2 py-0.5 "
                              + "text-[10px] "
                              + "font-semibold"
                            ),

                            statusClasses(
                              selected.status,
                            ),
                          ].join(
                            " ",
                          )}
                        >
                          {
                            humanize(
                              selected.status,
                            )
                          }
                        </span>


                        <span
                          className={[
                            (
                              "rounded-lg "
                              + "px-2 py-1 "
                              + "text-[10px] "
                              + "font-bold"
                            ),

                            priorityClasses(
                              selected.priority,
                            ),
                          ].join(
                            " ",
                          )}
                        >
                          {selected.priority}
                        </span>

                      </div>


                      <h2
                        className={
                          "mt-2 "
                          + "text-2xl "
                          + "font-semibold "
                          + "tracking-tight "
                          + "text-slate-950"
                        }
                      >
                        {selected.reference}
                      </h2>


                      <p
                        className={
                          "mt-2 "
                          + "text-sm "
                          + "text-slate-500"
                        }
                      >
                        {
                          humanize(
                            selected.channel,
                          )
                        }
                        {" / "}
                        {
                          humanize(
                            selected.intent,
                          )
                        }
                        {" / Updated "}
                        {
                          formatRelativeTime(
                            selected.updated_at,
                          )
                        }
                      </p>

                    </div>


                    <div
                      className={
                        "min-w-55 "
                        + "rounded-xl "
                        + "border border-slate-200 "
                        + "bg-slate-50 "
                        + "p-4"
                      }
                    >

                      <p
                        className={
                          "text-xs "
                          + "font-semibold "
                          + "uppercase "
                          + "tracking-wide "
                          + "text-slate-400"
                        }
                      >
                        Customer
                      </p>


                      <p
                        className={
                          "mt-2 "
                          + "font-medium "
                          + "text-slate-900"
                        }
                      >
                        {
                          selected.customer_name
                          ?? "Unverified customer"
                        }
                      </p>


                      <p
                        className={
                          "mt-1 "
                          + "text-xs "
                          + "text-slate-500"
                        }
                      >
                        {
                          selected.customer_email
                          ?? "No verified email"
                        }
                      </p>

                    </div>

                  </div>

                </header>


                <div
                  className={
                    "grid "
                    + "xl:grid-cols-"
                    + "[minmax(0,1fr)_350px]"
                  }
                >

                  <div
                    className={
                      "min-w-0 "
                      + "border-b "
                      + "border-slate-200 "
                      + "p-6 "
                      + "xl:border-b-0 "
                      + "xl:border-r"
                    }
                  >

                    <div
                      className={
                        "mb-5 flex "
                        + "items-center "
                        + "justify-between "
                        + "gap-3"
                      }
                    >

                      <h3
                        className={
                          "font-semibold "
                          + "text-slate-900"
                        }
                      >
                        Conversation
                      </h3>


                      <span
                        className={
                          "text-xs "
                          + "text-slate-400"
                        }
                      >
                        {
                          selected.messages.length
                        }
                        {
                          selected.messages.length
                            === 1
                            ? " message"
                            : " messages"
                        }
                      </span>

                    </div>


                    {
                      selected.messages.length
                      === 0
                      &&
                      (
                        <div
                          className={
                            "rounded-xl "
                            + "border "
                            + "border-dashed "
                            + "border-slate-200 "
                            + "p-8 "
                            + "text-center "
                            + "text-sm "
                            + "text-slate-500"
                          }
                        >
                          No conversation
                          messages are available.
                        </div>
                      )
                    }


                    <div
                      className="space-y-4"
                    >

                      {
                        selected.messages.map(
                          (message) => {

                            const customer =
                              message.sender_type
                                .toLowerCase()
                              === "customer";


                            return (
                              <article
                                key={
                                  message.id
                                }

                                className={[
                                  (
                                    "rounded-2xl "
                                    + "p-4 "
                                    + "text-sm "
                                    + "leading-6"
                                  ),

                                  message.is_internal
                                    ? (
                                      "border "
                                      + "border-amber-200 "
                                      + "bg-amber-50"
                                    )
                                    : customer
                                      ? (
                                        "mr-8 "
                                        + "bg-slate-100"
                                      )
                                      : (
                                        "ml-8 "
                                        + "border "
                                        + "border-slate-200 "
                                        + "bg-white"
                                      ),
                                ].join(
                                  " ",
                                )}
                              >

                                <div
                                  className={
                                    "mb-2 flex "
                                    + "items-center "
                                    + "justify-between "
                                    + "gap-4 "
                                    + "text-[10px] "
                                    + "font-medium "
                                    + "uppercase "
                                    + "tracking-wide "
                                    + "text-slate-400"
                                  }
                                >

                                  <span>
                                    {
                                      message.is_internal
                                        ? "Internal note"
                                        : humanize(
                                            message.sender_type,
                                          )
                                    }
                                  </span>


                                  <span
                                    className={
                                      "normal-case "
                                      + "tracking-normal"
                                    }
                                  >
                                    {
                                      new Date(
                                        message.sent_at,
                                      ).toLocaleString()
                                    }
                                  </span>

                                </div>


                                <p
                                  className={
                                    "whitespace-pre-wrap "
                                    + "text-slate-700"
                                  }
                                >
                                  {message.body}
                                </p>

                              </article>
                            );
                          },
                        )
                      }

                    </div>

                  </div>


                  <aside
                    className={
                      "space-y-6 "
                      + "bg-slate-50/60 "
                      + "p-6"
                    }
                  >

                    <section>

                      <h3
                        className={
                          "text-sm "
                          + "font-semibold "
                          + "text-slate-900"
                        }
                      >
                        Decision context
                      </h3>


                      <dl
                        className={
                          "mt-4 space-y-3 "
                          + "text-sm"
                        }
                      >

                        <div
                          className={
                            "flex "
                            + "justify-between "
                            + "gap-4"
                          }
                        >

                          <dt
                            className={
                              "text-slate-500"
                            }
                          >
                            Intent
                          </dt>

                          <dd
                            className={
                              "text-right "
                              + "font-medium "
                              + "text-slate-900"
                            }
                          >
                            {
                              humanize(
                                selected.intent,
                              )
                            }
                          </dd>

                        </div>


                        <div
                          className={
                            "flex "
                            + "justify-between "
                            + "gap-4"
                          }
                        >

                          <dt
                            className={
                              "text-slate-500"
                            }
                          >
                            Confidence
                          </dt>

                          <dd>
                            <span
                              className={[
                                (
                                  "rounded-full "
                                  + "px-2 py-1 "
                                  + "text-[10px] "
                                  + "font-semibold"
                                ),

                                confidenceClasses(
                                  selected
                                    .confidence_band,
                                ),
                              ].join(
                                " ",
                              )}
                            >
                              {
                                selected
                                  .confidence_band
                                ?? "NOT EVALUATED"
                              }
                            </span>
                          </dd>

                        </div>


                        <div
                          className={
                            "flex "
                            + "justify-between "
                            + "gap-4"
                          }
                        >

                          <dt
                            className={
                              "text-slate-500"
                            }
                          >
                            Restricted
                          </dt>

                          <dd
                            className={
                              "font-medium "
                              + (
                                selected
                                  .restricted_action
                                  ? "text-red-700"
                                  : "text-slate-900"
                              )
                            }
                          >
                            {
                              selected
                                .restricted_action
                                ? "Yes"
                                : "No"
                            }
                          </dd>

                        </div>


                        <div
                          className={
                            "flex "
                            + "justify-between "
                            + "gap-4"
                          }
                        >

                          <dt
                            className={
                              "text-slate-500"
                            }
                          >
                            Assignee
                          </dt>

                          <dd
                            className={
                              "text-right "
                              + "font-medium "
                              + "text-slate-900"
                            }
                          >
                            {
                              selected.assignee_name
                              ?? "Unassigned"
                            }
                          </dd>

                        </div>

                      </dl>


                      {
                        selected.escalation_reason
                        &&
                        (
                          <div
                            className={
                              "mt-4 rounded-xl "
                              + "border "
                              + "border-amber-200 "
                              + "bg-amber-50 "
                              + "p-3"
                            }
                          >

                            <p
                              className={
                                "text-[10px] "
                                + "font-semibold "
                                + "uppercase "
                                + "tracking-wide "
                                + "text-amber-700"
                              }
                            >
                              Escalation
                            </p>


                            <p
                              className={
                                "mt-1 "
                                + "text-xs "
                                + "leading-5 "
                                + "text-amber-900"
                              }
                            >
                              {
                                humanize(
                                  selected
                                    .escalation_reason,
                                )
                              }
                            </p>

                          </div>
                        )
                      }

                    </section>


                    <section
                      className={
                        "border-t "
                        + "border-slate-200 "
                        + "pt-6"
                      }
                    >

                      <div
                        className={
                          "flex "
                          + "items-center "
                          + "justify-between "
                          + "gap-3"
                        }
                      >

                        <h3
                          className={
                            "text-sm "
                            + "font-semibold "
                            + "text-slate-900"
                          }
                        >
                          Order context
                        </h3>


                        <span
                          className={
                            "text-xs "
                            + "text-slate-400"
                          }
                        >
                          {
                            selected.orders.length
                          }
                        </span>

                      </div>


                      {
                        selected.orders.length
                        === 0
                        ? (
                          <p
                            className={
                              "mt-3 "
                              + "text-sm "
                              + "leading-6 "
                              + "text-slate-500"
                            }
                          >
                            No verified order
                            context is attached.
                          </p>
                        )
                        : (
                          <div
                            className={
                              "mt-3 space-y-3"
                            }
                          >

                            {
                              selected.orders.map(
                                (order) => (
                                  <div
                                    key={
                                      order
                                        .external_order_id
                                    }

                                    className={
                                      "rounded-xl "
                                      + "border "
                                      + "border-slate-200 "
                                      + "bg-white "
                                      + "p-3"
                                    }
                                  >

                                    <div
                                      className={
                                        "flex "
                                        + "items-center "
                                        + "justify-between "
                                        + "gap-3"
                                      }
                                    >

                                      <p
                                        className={
                                          "text-sm "
                                          + "font-semibold "
                                          + "text-slate-900"
                                        }
                                      >
                                        {
                                          order
                                            .external_order_id
                                        }
                                      </p>


                                      <span
                                        className={
                                          "rounded-full "
                                          + "bg-slate-100 "
                                          + "px-2 py-1 "
                                          + "text-[10px] "
                                          + "font-medium "
                                          + "text-slate-600"
                                        }
                                      >
                                        {
                                          humanize(
                                            order.status,
                                          )
                                        }
                                      </span>

                                    </div>


                                    <p
                                      className={
                                        "mt-2 "
                                        + "text-[10px] "
                                        + "text-slate-400"
                                      }
                                    >
                                      Retrieved {
                                        formatRelativeTime(
                                          order
                                            .retrieved_at,
                                        )
                                      }
                                    </p>

                                  </div>
                                ),
                              )
                            }

                          </div>
                        )
                      }

                    </section>


                    <section
                      className={
                        "border-t "
                        + "border-slate-200 "
                        + "pt-6"
                      }
                    >

                      <div
                        className={
                          "flex "
                          + "items-center "
                          + "justify-between "
                          + "gap-3"
                        }
                      >

                        <h3
                          className={
                            "text-sm "
                            + "font-semibold "
                            + "text-slate-900"
                          }
                        >
                          Recent audit
                        </h3>


                        <span
                          className={
                            "text-xs "
                            + "text-slate-400"
                          }
                        >
                          {
                            selected
                              .audit_events
                              .length
                          }
                          {" total"}
                        </span>

                      </div>


                      <div
                        className={
                          "mt-4 space-y-3"
                        }
                      >

                        {
                          selected
                            .audit_events
                            .slice(
                              -5,
                            )
                            .reverse()
                            .map(
                              (event) => (
                                <div
                                  key={
                                    event.id
                                  }

                                  className={
                                    "border-l-2 "
                                    + "border-slate-200 "
                                    + "pl-3"
                                  }
                                >

                                  <p
                                    className={
                                      "text-xs "
                                      + "font-medium "
                                      + "text-slate-700"
                                    }
                                  >
                                    {
                                      humanize(
                                        event
                                          .event_type,
                                      )
                                    }
                                  </p>


                                  <p
                                    className={
                                      "mt-1 "
                                      + "text-[10px] "
                                      + "text-slate-400"
                                    }
                                  >
                                    {
                                      event.actor_type
                                    }
                                    {" / "}
                                    {
                                      formatRelativeTime(
                                        event.created_at,
                                      )
                                    }
                                  </p>

                                </div>
                              ),
                            )
                        }


                        {
                          selected
                            .audit_events
                            .length
                          === 0
                          &&
                          (
                            <p
                              className={
                                "text-sm "
                                + "text-slate-500"
                              }
                            >
                              No audit events
                              recorded.
                            </p>
                          )
                        }

                      </div>

                    </section>

                  </aside>

                </div>

              </div>
            )
          }

        </section>

      </div>

    </main>
  );
}