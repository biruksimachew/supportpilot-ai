"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useParams,
  useRouter,
} from "next/navigation";

import {
  addAgentInternalNote,
  assignAgentTicketToSelf,
  escalateAgentTicket,
  getAgentTicket,
  resolveAgentTicket,
  sendAgentReply,
  StaffApiError,
} from "@/lib/staff-api";

import {
  getSupabaseBrowserClient,
} from "@/lib/supabase-browser";

import type {
  AgentResolutionCode,
  AgentTicketDetail,
  ConfidenceBand,
  TicketPriority,
  TicketStatus,
} from "@/lib/staff-types";

import StaffShell
  from "@/components/staff-shell";


type ContextTab =
  | "decision"
  | "evidence"
  | "audit";


const RESOLUTION_OPTIONS:
  {
    value: AgentResolutionCode;
    label: string;
  }[] = [
    {
      value:
        "AGENT_RESOLVED",
      label:
        "Resolved by agent",
    },
    {
      value:
        "CUSTOMER_INFO_REQUIRED",
      label:
        "Customer info required",
    },
    {
      value:
        "POLICY_EXCEPTION",
      label:
        "Policy exception",
    },
    {
      value:
        "ORDER_ACTION_REQUIRED",
      label:
        "Order action required",
    },
    {
      value:
        "TECHNICAL_FAILURE",
      label:
        "Technical failure",
    },
    {
      value:
        "DUPLICATE",
      label:
        "Duplicate",
    },
    {
      value:
        "SPAM",
      label:
        "Spam",
    },
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


function summarizeRecord(
  value:
    Record<string, unknown>,
): string {
  const entries =
    Object.entries(value)
      .slice(0, 4);

  if (
    entries.length === 0
  ) {
    return "No summary";
  }

  return entries
    .map(
      (
        [
          key,
          entryValue,
        ],
      ) => {
        const normalized =
          typeof entryValue
          === "object"
          &&
          entryValue !== null
            ? JSON.stringify(
                entryValue,
              )
            : String(
                entryValue,
              );

        return (
          `${humanize(key)}: `
          + normalized
        );
      },
    )
    .join(" · ");
}


export default function TicketWorkspace() {
  const router =
    useRouter();

  const params =
    useParams<{
      ticketId: string;
    }>();

  const ticketId =
    typeof params.ticketId
    === "string"
      ? params.ticketId
      : "";

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
    ticket,
    setTicket,
  ] =
    useState<
      AgentTicketDetail | null
    >(null);

  const [
    authLoading,
    setAuthLoading,
  ] =
    useState(true);

  const [
    detailLoading,
    setDetailLoading,
  ] =
    useState(true);

  const [
    actionBusy,
    setActionBusy,
  ] =
    useState<
      string | null
    >(null);

  const [
    error,
    setError,
  ] =
    useState<
      string | null
    >(null);

  const [
    notice,
    setNotice,
  ] =
    useState<
      string | null
    >(null);

  const [
    contextTab,
    setContextTab,
  ] =
    useState<
      ContextTab
    >("decision");

  const [
    composerMode,
    setComposerMode,
  ] =
    useState<
      "reply"
      | "note"
    >("reply");

  const [
    replyBody,
    setReplyBody,
  ] =
    useState("");

  const [
    replyDirty,
    setReplyDirty,
  ] =
    useState(false);

  const [
    noteBody,
    setNoteBody,
  ] =
    useState("");

  const [
    replyIdempotencyKey,
    setReplyIdempotencyKey,
  ] =
    useState<
      string | null
    >(null);

  const [
    attemptedReplyBody,
    setAttemptedReplyBody,
  ] =
    useState<
      string | null
    >(null);

  const [
    deliveryBlocked,
    setDeliveryBlocked,
  ] =
    useState(false);

  const [
    escalationReason,
    setEscalationReason,
  ] =
    useState("");

  const [
    escalationPriority,
    setEscalationPriority,
  ] =
    useState<
      TicketPriority
    >("P2");

  const [
    resolutionCode,
    setResolutionCode,
  ] =
    useState<
      AgentResolutionCode
    >("AGENT_RESOLVED");


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


  const loadTicket =
    useCallback(
      async (
        preserveComposer:
          boolean,
      ) => {
        if (
          !accessToken
          ||
          !ticketId
        ) {
          return;
        }

        try {
          const detail =
            await getAgentTicket(
              accessToken,
              ticketId,
            );

          setTicket(
            detail,
          );

          setEscalationPriority(
            detail.priority,
          );

          if (
            !preserveComposer
          ) {
            setReplyBody(
              detail.latest_draft
                ?.original_body
              ?? "",
            );

            setReplyDirty(
              false,
            );

            setReplyIdempotencyKey(
              null,
            );

            setAttemptedReplyBody(
              null,
            );

            setDeliveryBlocked(
              false,
            );
          }
        } catch (caught) {
          if (
            caught
              instanceof StaffApiError
          ) {
            if (
              caught.status
                === 401
              ||
              caught.status
                === 403
            ) {
              await handleAuthFailure();
              return;
            }

            setError(
              caught.message,
            );
            return;
          }

          setError(
            "The ticket workspace could not be loaded.",
          );
        }
      },
      [
        accessToken,
        handleAuthFailure,
        ticketId,
      ],
    );


  useEffect(() => {
    if (
      authLoading
      ||
      !accessToken
      ||
      !ticketId
    ) {
      return;
    }

    let cancelled =
      false;

    void getAgentTicket(
      accessToken,
      ticketId,
    )
      .then(
        (detail) => {
          if (cancelled) {
            return;
          }

          setTicket(
            detail,
          );

          setEscalationPriority(
            detail.priority,
          );

          setReplyBody(
            detail.latest_draft
              ?.original_body
            ?? "",
          );

          setReplyDirty(
            false,
          );

          setReplyIdempotencyKey(
            null,
          );

          setAttemptedReplyBody(
            null,
          );

          setDeliveryBlocked(
            false,
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
          ) {
            if (
              caught.status
                === 401
              ||
              caught.status
                === 403
            ) {
              void handleAuthFailure();
              return;
            }

            setError(
              caught.message,
            );
            return;
          }

          setError(
            "The ticket workspace could not be loaded.",
          );
        },
      )
      .finally(
        () => {
          if (!cancelled) {
            setDetailLoading(
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
    handleAuthFailure,
    ticketId,
  ]);

  async function refreshTicket(
    preserveComposer = true,
  ) {
    setDetailLoading(
      true,
    );

    try {
      await loadTicket(
        preserveComposer,
      );
    } finally {
      setDetailLoading(
        false,
      );
    }
  }


  async function runAction(
    actionName: string,
    action:
      () => Promise<unknown>,
    successMessage: string,
  ): Promise<boolean> {
    setActionBusy(
      actionName,
    );

    setError(
      null,
    );

    setNotice(
      null,
    );

    try {
      await action();

      setNotice(
        successMessage,
      );

      await refreshTicket(
        true,
      );

      return true;
    } catch (caught) {
      if (
        caught
          instanceof StaffApiError
      ) {
        if (
          caught.status
            === 401
          ||
          caught.status
            === 403
        ) {
          await handleAuthFailure();
          return false;
        }

        setError(
          caught.message,
        );
        return false;
      }

      setError(
        "The agent action could not be completed.",
      );

      return false;
    } finally {
      setActionBusy(
        null,
      );
    }
  }


  async function sendReply() {
    if (
      !accessToken
      ||
      !ticket
      ||
      !replyBody.trim()
      ||
      deliveryBlocked
    ) {
      return;
    }

    const normalizedBody =
      replyBody.trim();

    const idempotencyKey =
      (
        replyIdempotencyKey
        &&
        attemptedReplyBody
          === normalizedBody
      )
        ? replyIdempotencyKey
        : crypto.randomUUID();

    setReplyIdempotencyKey(
      idempotencyKey,
    );

    setAttemptedReplyBody(
      normalizedBody,
    );

    setActionBusy(
      "send",
    );

    setError(
      null,
    );

    setNotice(
      null,
    );

    try {
      await sendAgentReply(
        accessToken,
        ticket.id,
        idempotencyKey,
        normalizedBody,
      );

      setNotice(
        ticket.channel
          === "email"
          ? "Email reply delivered."
          : "Chat reply delivered.",
      );

      setReplyBody("");
      setReplyDirty(false);
      setReplyIdempotencyKey(
        null,
      );
      setAttemptedReplyBody(
        null,
      );

      await refreshTicket(
        true,
      );
    } catch (caught) {
      if (
        caught
          instanceof StaffApiError
      ) {
        if (
          caught.status
            === 401
          ||
          caught.status
            === 403
        ) {
          await handleAuthFailure();
          return;
        }

        if (
          caught.code
          === "DELIVERY_UNCERTAIN"
        ) {
          setDeliveryBlocked(
            true,
          );

          setError(
            (
              "Delivery could not be confirmed. "
              + "Sending is locked for this ticket "
              + "to prevent a duplicate. Inspect "
              + "the delivery state before retrying."
            ),
          );

          return;
        }

        if (
          caught.code
          === "DELIVERY_CONFIRMED_FAILED"
        ) {
          setError(
            (
              caught.message
              + " You can retry the unchanged "
              + "reply; SupportPilot will reuse "
              + "the same idempotency key."
            ),
          );

          return;
        }

        setError(
          caught.message,
        );
        return;
      }

      setError(
        "The reply could not be delivered.",
      );
    } finally {
      setActionBusy(
        null,
      );
    }
  }


  async function addNote() {
    if (
      !accessToken
      ||
      !ticket
      ||
      !noteBody.trim()
    ) {
      return;
    }

    const body =
      noteBody.trim();

    const succeeded =
      await runAction(
        "note",
        () =>
          addAgentInternalNote(
            accessToken,
            ticket.id,
            body,
          ),
        "Internal note added.",
      );

    if (succeeded) {
      setNoteBody("");
    }
  }


  async function assignSelf() {
    if (
      !accessToken
      ||
      !ticket
    ) {
      return;
    }

    await runAction(
      "assign",
      () =>
        assignAgentTicketToSelf(
          accessToken,
          ticket.id,
        ),
      "Ticket assigned to you.",
    );
  }


  async function escalate() {
    if (
      !accessToken
      ||
      !ticket
      ||
      !escalationReason.trim()
    ) {
      return;
    }

    const reason =
      escalationReason.trim();

    const succeeded =
      await runAction(
        "escalate",
        () =>
          escalateAgentTicket(
            accessToken,
            ticket.id,
            reason,
            escalationPriority,
          ),
        "Ticket escalated for human review.",
      );

    if (succeeded) {
      setEscalationReason("");
    }
  }


  async function resolve() {
    if (
      !accessToken
      ||
      !ticket
    ) {
      return;
    }

    const confirmed =
      window.confirm(
        (
          "Resolve this ticket with "
          + humanize(
              resolutionCode,
            )
          + "?"
        ),
      );

    if (!confirmed) {
      return;
    }

    await runAction(
      "resolve",
      () =>
        resolveAgentTicket(
          accessToken,
          ticket.id,
          resolutionCode,
        ),
      "Ticket resolved.",
    );
  }


  const conversation =
    useMemo(
      () =>
        ticket?.messages
          .filter(
            (message) =>
              !message.is_internal,
          )
        ?? [],
      [
        ticket,
      ],
    );


  const internalNotes =
    useMemo(
      () =>
        ticket?.messages
          .filter(
            (message) =>
              message.is_internal,
          )
        ?? [],
      [
        ticket,
      ],
    );


  if (
    authLoading
    ||
    (
      detailLoading
      &&
      !ticket
    )
  ) {
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
        Loading ticket workspace...
      </div>
    );
  }


  if (!ticket) {
    return (
      <StaffShell
        active="queue"
        title="Ticket unavailable"
        subtitle={
          "The requested ticket could not be loaded."
        }
        staffEmail={
          staffEmail
        }
      >
        <div
          className={
            "mx-auto max-w-3xl "
            + "p-6"
          }
        >
          <div
            className={
              "rounded-2xl "
              + "border border-red-200 "
              + "bg-white p-8 "
              + "text-center "
              + "shadow-sm"
            }
          >
            <p
              className={
                "font-semibold "
                + "text-slate-900"
              }
            >
              Ticket unavailable
            </p>

            <p
              className={
                "mt-2 text-sm "
                + "text-slate-500"
              }
            >
              {
                error
                ?? "No ticket data was returned."
              }
            </p>

            <button
              type="button"
              onClick={
                () =>
                  router.push(
                    "/staff",
                  )
              }
              className={
                "mt-5 rounded-xl "
                + "bg-slate-950 "
                + "px-4 py-2.5 "
                + "text-sm "
                + "font-semibold "
                + "text-white"
              }
            >
              Back to queue
            </button>
          </div>
        </div>
      </StaffShell>
    );
  }


  return (
    <StaffShell
      active="queue"
      title={
        ticket.reference
      }
      subtitle={
        (
          humanize(
            ticket.channel,
          )
          + " · "
          + humanize(
              ticket.intent,
            )
          + " · Updated "
          + formatRelativeTime(
              ticket.updated_at,
            )
        )
      }
      staffEmail={
        staffEmail
      }
      onRefresh={
        () =>
          void refreshTicket(
            true,
          )
      }
      refreshBusy={
        detailLoading
      }
    >
      <div
        className={
          "mx-auto max-w-[1580px] "
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

        {notice && (
          <div
            className={
              "rounded-xl "
              + "border "
              + "border-emerald-200 "
              + "bg-emerald-50 "
              + "px-4 py-3 "
              + "text-sm "
              + "text-emerald-800"
            }
          >
            {notice}
          </div>
        )}

        <section
          className={
            "rounded-2xl "
            + "border "
            + "border-slate-200 "
            + "bg-white "
            + "p-4 "
            + "shadow-sm "
            + "sm:p-5"
          }
        >
          <div
            className={
              "flex flex-wrap "
              + "items-start "
              + "justify-between "
              + "gap-4"
            }
          >
            <div>
              <button
                type="button"
                onClick={
                  () =>
                    router.push(
                      "/staff",
                    )
                }
                className={
                  "text-xs "
                  + "font-semibold "
                  + "text-slate-500 "
                  + "transition "
                  + "hover:text-slate-950"
                }
              >
                ← Back to queue
              </button>

              <div
                className={
                  "mt-3 flex "
                  + "flex-wrap "
                  + "items-center "
                  + "gap-2"
                }
              >
                <h1
                  className={
                    "text-2xl "
                    + "font-semibold "
                    + "tracking-tight"
                  }
                >
                  {ticket.reference}
                </h1>

                <span
                  className={[
                    (
                      "rounded-full "
                      + "border "
                      + "px-2.5 py-1 "
                      + "text-[10px] "
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
                      "rounded-lg "
                      + "px-2.5 py-1 "
                      + "text-[10px] "
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
                  "mt-2 text-sm "
                  + "text-slate-500"
                }
              >
                {
                  ticket.customer_name
                  ?? "Unverified customer"
                }
                {
                  ticket.customer_email
                    ? (
                      " · "
                      + ticket.customer_email
                    )
                    : ""
                }
              </p>
            </div>

            <div
              className={
                "flex flex-wrap "
                + "items-center "
                + "gap-2"
              }
            >
              <span
                className={[
                  (
                    "rounded-full "
                    + "px-2.5 py-1 "
                    + "text-[10px] "
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

              <span
                className={
                  (
                    "rounded-full "
                    + "px-2.5 py-1 "
                    + "text-[10px] "
                    + "font-semibold "
                  )
                  + (
                    ticket.restricted_action
                      ? (
                        "bg-red-100 "
                        + "text-red-800"
                      )
                      : (
                        "bg-slate-100 "
                        + "text-slate-600"
                      )
                  )
                }
              >
                {
                  ticket.restricted_action
                    ? "Restricted action"
                    : "No restricted action"
                }
              </span>
            </div>
          </div>
        </section>

        <div
          className={
            "grid gap-4 "
            + "xl:grid-cols-"
            + "[minmax(0,1fr)_390px]"
          }
        >
          <main
            className={
              "space-y-4"
            }
          >
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
                  "flex items-center "
                  + "justify-between "
                  + "gap-3 "
                  + "border-b "
                  + "border-slate-200 "
                  + "px-5 py-4"
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
                    Conversation
                  </p>

                  <h2
                    className={
                      "mt-1 text-base "
                      + "font-semibold"
                    }
                  >
                    Customer thread
                  </h2>
                </div>

                <span
                  className={
                    "text-xs "
                    + "text-slate-400"
                  }
                >
                  {
                    conversation.length
                  }
                  {
                    conversation.length
                      === 1
                      ? " message"
                      : " messages"
                  }
                </span>
              </div>

              <div
                className={
                  "space-y-4 "
                  + "p-5"
                }
              >
                {
                  conversation.length
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
                      No customer-visible
                      messages yet.
                    </div>
                  )
                }

                {conversation.map(
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
                            "max-w-[88%] "
                            + "rounded-2xl "
                            + "p-4 "
                            + "text-sm "
                            + "leading-6"
                          ),
                          customer
                            ? (
                              "mr-auto "
                              + "bg-slate-100 "
                              + "text-slate-700"
                            )
                            : (
                              "ml-auto "
                              + "border "
                              + "border-slate-200 "
                              + "bg-white "
                              + "text-slate-700"
                            ),
                        ].join(" ")}
                      >
                        <div
                          className={
                            "mb-2 flex "
                            + "items-center "
                            + "justify-between "
                            + "gap-4 "
                            + "text-[10px] "
                            + "font-semibold "
                            + "uppercase "
                            + "tracking-wide "
                            + "text-slate-400"
                          }
                        >
                          <span>
                            {
                              humanize(
                                message
                                  .sender_type,
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
                                message
                                  .sent_at,
                              )
                                .toLocaleString()
                            }
                          </span>
                        </div>

                        <p
                          className={
                            "whitespace-pre-wrap"
                          }
                        >
                          {message.body}
                        </p>
                      </article>
                    );
                  },
                )}
              </div>
            </section>

            <section
              className={
                "rounded-2xl "
                + "border "
                + "border-slate-200 "
                + "bg-white "
                + "shadow-sm"
              }
            >
              <div
                className={
                  "flex gap-1 "
                  + "border-b "
                  + "border-slate-200 "
                  + "bg-slate-50 "
                  + "p-1"
                }
              >
                <button
                  type="button"
                  onClick={
                    () =>
                      setComposerMode(
                        "reply",
                      )
                  }
                  className={[
                    (
                      "flex-1 rounded-lg "
                      + "px-3 py-2 "
                      + "text-xs "
                      + "font-semibold "
                      + "transition"
                    ),
                    composerMode
                      === "reply"
                        ? (
                          "bg-white "
                          + "text-slate-950 "
                          + "shadow-sm"
                        )
                        : "text-slate-500",
                  ].join(" ")}
                >
                  Customer reply
                </button>

                <button
                  type="button"
                  onClick={
                    () =>
                      setComposerMode(
                        "note",
                      )
                  }
                  className={[
                    (
                      "flex-1 rounded-lg "
                      + "px-3 py-2 "
                      + "text-xs "
                      + "font-semibold "
                      + "transition"
                    ),
                    composerMode
                      === "note"
                        ? (
                          "bg-white "
                          + "text-slate-950 "
                          + "shadow-sm"
                        )
                        : "text-slate-500",
                  ].join(" ")}
                >
                  Internal note
                </button>
              </div>

              {
                composerMode
                === "reply"
                ? (
                  <div
                    className={
                      "p-4 sm:p-5"
                    }
                  >
                    {
                      ticket.latest_draft
                      &&
                      (
                        <div
                          className={
                            "mb-3 flex "
                            + "flex-wrap "
                            + "items-center "
                            + "justify-between "
                            + "gap-2 "
                            + "rounded-xl "
                            + "bg-violet-50 "
                            + "px-3 py-2 "
                            + "text-[10px] "
                            + "text-violet-700"
                          }
                        >
                          <span>
                            AI draft captured {
                              formatRelativeTime(
                                ticket
                                  .latest_draft
                                  .created_at,
                              )
                            }
                          </span>

                          {
                            replyDirty
                            &&
                            (
                              <span
                                className={
                                  "font-semibold"
                                }
                              >
                                Agent edited
                              </span>
                            )
                          }
                        </div>
                      )
                    }

                    <textarea
                      value={
                        replyBody
                      }
                      onChange={
                        (event) => {
                          setReplyBody(
                            event
                              .target
                              .value,
                          );

                          setReplyDirty(
                            true,
                          );
                        }
                      }
                      rows={8}
                      placeholder={
                        ticket.latest_draft
                          ? "Review and edit the AI draft..."
                          : "Write a customer reply..."
                      }
                      className={
                        "w-full resize-y "
                        + "rounded-xl "
                        + "border "
                        + "border-slate-200 "
                        + "bg-white "
                        + "px-4 py-3 "
                        + "text-sm "
                        + "leading-6 "
                        + "text-slate-800 "
                        + "outline-none "
                        + "transition "
                        + "focus:border-slate-400"
                      }
                    />

                    {
                      deliveryBlocked
                      &&
                      (
                        <p
                          className={
                            "mt-2 text-xs "
                            + "font-medium "
                            + "text-red-700"
                          }
                        >
                          Sending is locked because
                          the previous provider
                          outcome is uncertain.
                        </p>
                      )
                    }

                    <div
                      className={
                        "mt-3 flex "
                        + "flex-wrap "
                        + "items-center "
                        + "justify-between "
                        + "gap-3"
                      }
                    >
                      <p
                        className={
                          "text-xs "
                          + "text-slate-400"
                        }
                      >
                        {
                          ticket.channel
                            === "email"
                            ? (
                              "Replies through "
                              + "the Gmail delivery "
                              + "adapter."
                            )
                            : (
                              "Replies through "
                              + "the chat delivery "
                              + "adapter."
                            )
                        }
                      </p>

                      <button
                        type="button"
                        disabled={
                          actionBusy
                            !== null
                          ||
                          !replyBody.trim()
                          ||
                          deliveryBlocked
                        }
                        onClick={
                          () =>
                            void sendReply()
                        }
                        className={
                          "rounded-xl "
                          + "bg-slate-950 "
                          + "px-5 py-2.5 "
                          + "text-sm "
                          + "font-semibold "
                          + "text-white "
                          + "transition "
                          + "hover:bg-slate-800 "
                          + "disabled:opacity-40"
                        }
                      >
                        {
                          actionBusy
                          === "send"
                            ? "Sending..."
                            : (
                              "Send "
                              + (
                                ticket.channel
                                  === "email"
                                  ? "email"
                                  : "reply"
                              )
                            )
                        }
                      </button>
                    </div>
                  </div>
                )
                : (
                  <div
                    className={
                      "p-4 sm:p-5"
                    }
                  >
                    <textarea
                      value={
                        noteBody
                      }
                      onChange={
                        (event) =>
                          setNoteBody(
                            event
                              .target
                              .value,
                          )
                      }
                      rows={6}
                      placeholder={
                        "Add a private note for the support team..."
                      }
                      className={
                        "w-full resize-y "
                        + "rounded-xl "
                        + "border "
                        + "border-amber-200 "
                        + "bg-amber-50/40 "
                        + "px-4 py-3 "
                        + "text-sm "
                        + "leading-6 "
                        + "outline-none"
                      }
                    />

                    <div
                      className={
                        "mt-3 flex "
                        + "justify-end"
                      }
                    >
                      <button
                        type="button"
                        disabled={
                          actionBusy
                            !== null
                          ||
                          !noteBody.trim()
                        }
                        onClick={
                          () =>
                            void addNote()
                        }
                        className={
                          "rounded-xl "
                          + "bg-amber-700 "
                          + "px-5 py-2.5 "
                          + "text-sm "
                          + "font-semibold "
                          + "text-white "
                          + "disabled:opacity-40"
                        }
                      >
                        {
                          actionBusy
                          === "note"
                            ? "Saving..."
                            : "Add internal note"
                        }
                      </button>
                    </div>

                    {
                      internalNotes.length
                      > 0
                      &&
                      (
                        <div
                          className={
                            "mt-5 space-y-3 "
                            + "border-t "
                            + "border-slate-200 "
                            + "pt-5"
                          }
                        >
                          {
                            internalNotes
                              .slice()
                              .reverse()
                              .map(
                                (message) => (
                                  <div
                                    key={
                                      message.id
                                    }
                                    className={
                                      "rounded-xl "
                                      + "border "
                                      + "border-amber-200 "
                                      + "bg-amber-50 "
                                      + "p-3"
                                    }
                                  >
                                    <p
                                      className={
                                        "whitespace-pre-wrap "
                                        + "text-sm "
                                        + "text-amber-950"
                                      }
                                    >
                                      {message.body}
                                    </p>

                                    <p
                                      className={
                                        "mt-2 text-[10px] "
                                        + "text-amber-700"
                                      }
                                    >
                                      {
                                        formatRelativeTime(
                                          message
                                            .sent_at,
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
                  </div>
                )
              }
            </section>
          </main>

          <aside
            className={
              "space-y-4 "
              + "xl:sticky "
              + "xl:top-20 "
              + "xl:self-start"
            }
          >
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
              <p
                className={
                  "text-[10px] "
                  + "font-bold "
                  + "uppercase "
                  + "tracking-[0.16em] "
                  + "text-slate-400"
                }
              >
                Customer
              </p>

              <p
                className={
                  "mt-2 text-sm "
                  + "font-semibold"
                }
              >
                {
                  ticket.customer_name
                  ?? "Unverified customer"
                }
              </p>

              <p
                className={
                  "mt-1 text-xs "
                  + "text-slate-500"
                }
              >
                {
                  ticket.customer_email
                  ?? "No verified email"
                }
              </p>

              <div
                className={
                  "mt-4 grid "
                  + "grid-cols-2 gap-2"
                }
              >
                <div
                  className={
                    "rounded-xl "
                    + "bg-slate-50 "
                    + "p-3"
                  }
                >
                  <p
                    className={
                      "text-[9px] "
                      + "uppercase "
                      + "tracking-wide "
                      + "text-slate-400"
                    }
                  >
                    Identity
                  </p>

                  <p
                    className={
                      "mt-1 text-xs "
                      + "font-semibold "
                      + "text-slate-700"
                    }
                  >
                    {
                      humanize(
                        ticket
                          .identity_verification_status,
                      )
                    }
                  </p>
                </div>

                <div
                  className={
                    "rounded-xl "
                    + "bg-slate-50 "
                    + "p-3"
                  }
                >
                  <p
                    className={
                      "text-[9px] "
                      + "uppercase "
                      + "tracking-wide "
                      + "text-slate-400"
                    }
                  >
                    Assignee
                  </p>

                  <p
                    className={
                      "mt-1 truncate "
                      + "text-xs "
                      + "font-semibold "
                      + "text-slate-700"
                    }
                  >
                    {
                      ticket.assignee_name
                      ?? "Unassigned"
                    }
                  </p>
                </div>
              </div>

              {
                ticket.escalation_reason
                &&
                (
                  <div
                    className={
                      "mt-3 rounded-xl "
                      + "border "
                      + "border-amber-200 "
                      + "bg-amber-50 "
                      + "p-3"
                    }
                  >
                    <p
                      className={
                        "text-[9px] "
                        + "font-bold "
                        + "uppercase "
                        + "tracking-wide "
                        + "text-amber-700"
                      }
                    >
                      Escalation
                    </p>

                    <p
                      className={
                        "mt-1 text-xs "
                        + "leading-5 "
                        + "text-amber-900"
                      }
                    >
                      {
                        ticket
                          .escalation_reason
                      }
                    </p>
                  </div>
                )
              }
            </section>

            <section
              className={
                "rounded-2xl "
                + "border "
                + "border-slate-200 "
                + "bg-white "
                + "shadow-sm"
              }
            >
              <div
                className={
                  "flex gap-1 "
                  + "border-b "
                  + "border-slate-200 "
                  + "p-1"
                }
              >
                {
                  (
                    [
                      "decision",
                      "evidence",
                      "audit",
                    ] as ContextTab[]
                  ).map(
                    (tab) => (
                      <button
                        key={
                          tab
                        }
                        type="button"
                        onClick={
                          () =>
                            setContextTab(
                              tab,
                            )
                        }
                        className={[
                          (
                            "flex-1 "
                            + "rounded-lg "
                            + "px-2 py-2 "
                            + "text-[10px] "
                            + "font-semibold "
                            + "transition"
                          ),
                          contextTab
                            === tab
                              ? (
                                "bg-slate-950 "
                                + "text-white"
                              )
                              : (
                                "text-slate-500 "
                                + "hover:bg-slate-50"
                              ),
                        ].join(" ")}
                      >
                        {
                          humanize(
                            tab,
                          )
                        }
                      </button>
                    ),
                  )
                }
              </div>

              <div
                className={
                  "p-4"
                }
              >
                {
                  contextTab
                  === "decision"
                  &&
                  (
                    <div
                      className={
                        "space-y-4"
                      }
                    >
                      {
                        ticket.latest_ai_run
                        ? (
                          <>
                            <div>
                              <p
                                className={
                                  "text-[9px] "
                                  + "font-bold "
                                  + "uppercase "
                                  + "tracking-wide "
                                  + "text-slate-400"
                                }
                              >
                                Decision
                              </p>

                              <p
                                className={
                                  "mt-1 text-sm "
                                  + "font-semibold"
                                }
                              >
                                {
                                  humanize(
                                    ticket
                                      .latest_ai_run
                                      .decision,
                                  )
                                }
                              </p>
                            </div>

                            <div
                              className={
                                "grid "
                                + "grid-cols-2 "
                                + "gap-2"
                              }
                            >
                              <div
                                className={
                                  "rounded-xl "
                                  + "bg-slate-50 "
                                  + "p-3"
                                }
                              >
                                <p
                                  className={
                                    "text-[9px] "
                                    + "uppercase "
                                    + "text-slate-400"
                                  }
                                >
                                  Safe draft
                                </p>

                                <p
                                  className={
                                    "mt-1 text-xs "
                                    + "font-semibold"
                                  }
                                >
                                  {
                                    ticket
                                      .latest_ai_run
                                      .safe_draft_ready
                                      ? "Ready"
                                      : "No"
                                  }
                                </p>
                              </div>

                              <div
                                className={
                                  "rounded-xl "
                                  + "bg-slate-50 "
                                  + "p-3"
                                }
                              >
                                <p
                                  className={
                                    "text-[9px] "
                                    + "uppercase "
                                    + "text-slate-400"
                                  }
                                >
                                  Auto eligible
                                </p>

                                <p
                                  className={
                                    "mt-1 text-xs "
                                    + "font-semibold"
                                  }
                                >
                                  {
                                    ticket
                                      .latest_ai_run
                                      .auto_response_eligible
                                      ? "Yes"
                                      : "No"
                                  }
                                </p>
                              </div>
                            </div>

                            <div>
                              <p
                                className={
                                  "text-[9px] "
                                  + "font-bold "
                                  + "uppercase "
                                  + "tracking-wide "
                                  + "text-slate-400"
                                }
                              >
                                Reasons
                              </p>

                              <div
                                className={
                                  "mt-2 "
                                  + "space-y-2"
                                }
                              >
                                {
                                  ticket
                                    .latest_ai_run
                                    .decision_reasons
                                    .map(
                                      (reason) => (
                                        <div
                                          key={
                                            reason
                                          }
                                          className={
                                            "rounded-lg "
                                            + "bg-slate-50 "
                                            + "px-3 py-2 "
                                            + "text-xs "
                                            + "text-slate-600"
                                          }
                                        >
                                          {
                                            humanize(
                                              reason,
                                            )
                                          }
                                        </div>
                                      ),
                                    )
                                }
                              </div>
                            </div>

                            {
                              ticket.tool_calls
                                .length
                              > 0
                              &&
                              (
                                <div>
                                  <p
                                    className={
                                      "text-[9px] "
                                      + "font-bold "
                                      + "uppercase "
                                      + "tracking-wide "
                                      + "text-slate-400"
                                    }
                                  >
                                    Tool calls
                                  </p>

                                  <div
                                    className={
                                      "mt-2 "
                                      + "space-y-2"
                                    }
                                  >
                                    {
                                      ticket
                                        .tool_calls
                                        .map(
                                          (tool) => (
                                            <div
                                              key={
                                                tool.id
                                              }
                                              className={
                                                "rounded-xl "
                                                + "border "
                                                + "border-slate-200 "
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
                                                    "text-xs "
                                                    + "font-semibold"
                                                  }
                                                >
                                                  {
                                                    humanize(
                                                      tool
                                                        .tool_name,
                                                    )
                                                  }
                                                </p>

                                                <span
                                                  className={
                                                    "text-[9px] "
                                                    + "text-slate-400"
                                                  }
                                                >
                                                  {
                                                    humanize(
                                                      tool.status,
                                                    )
                                                  }
                                                </span>
                                              </div>

                                              {
                                                tool
                                                  .result_summary
                                                &&
                                                (
                                                  <p
                                                    className={
                                                      "mt-2 text-[10px] "
                                                      + "leading-5 "
                                                      + "text-slate-500"
                                                    }
                                                  >
                                                    {
                                                      tool
                                                        .result_summary
                                                    }
                                                  </p>
                                                )
                                              }
                                            </div>
                                          ),
                                        )
                                    }
                                  </div>
                                </div>
                              )
                            }
                          </>
                        )
                        : (
                          <p
                            className={
                              "text-sm "
                              + "text-slate-500"
                            }
                          >
                            No AI decision has been
                            persisted for this ticket.
                          </p>
                        )
                      }
                    </div>
                  )
                }

                {
                  contextTab
                  === "evidence"
                  &&
                  (
                    <div
                      className={
                        "space-y-3"
                      }
                    >
                      {
                        ticket
                          .retrieval_evidence
                          .length
                        === 0
                        ? (
                          <p
                            className={
                              "text-sm "
                              + "text-slate-500"
                            }
                          >
                            No retrieval evidence
                            attached.
                          </p>
                        )
                        : (
                          ticket
                            .retrieval_evidence
                            .map(
                              (evidence) => (
                                <article
                                  key={
                                    (
                                      evidence
                                        .chunk_id
                                      + "-"
                                      + evidence.rank
                                    )
                                  }
                                  className={
                                    "rounded-xl "
                                    + "border "
                                    + "border-slate-200 "
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
                                        "truncate "
                                        + "text-xs "
                                        + "font-semibold"
                                      }
                                    >
                                      {
                                        evidence
                                          .source_title
                                      }
                                    </p>

                                    <span
                                      className={
                                        "text-[9px] "
                                        + "text-slate-400"
                                      }
                                    >
                                      Rank {
                                        evidence.rank
                                      }
                                    </span>
                                  </div>

                                  <p
                                    className={
                                      "mt-2 "
                                      + "line-clamp-5 "
                                      + "text-[10px] "
                                      + "leading-5 "
                                      + "text-slate-500"
                                    }
                                  >
                                    {
                                      evidence.content
                                    }
                                  </p>
                                </article>
                              ),
                            )
                        )
                      }
                    </div>
                  )
                }

                {
                  contextTab
                  === "audit"
                  &&
                  (
                    <div
                      className={
                        "space-y-3"
                      }
                    >
                      {
                        ticket
                          .audit_events
                          .length
                        === 0
                        ? (
                          <p
                            className={
                              "text-sm "
                              + "text-slate-500"
                            }
                          >
                            No audit events recorded.
                          </p>
                        )
                        : (
                          ticket
                            .audit_events
                            .slice()
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
                                      + "font-semibold "
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
                                      "mt-1 text-[9px] "
                                      + "text-slate-400"
                                    }
                                  >
                                    {
                                      humanize(
                                        event
                                          .actor_type,
                                      )
                                    }
                                    {" · "}
                                    {
                                      formatRelativeTime(
                                        event
                                          .created_at,
                                      )
                                    }
                                  </p>
                                </div>
                              ),
                            )
                        )
                      }
                    </div>
                  )
                }
              </div>
            </section>

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
                  "flex items-center "
                  + "justify-between "
                  + "gap-3"
                }
              >
                <p
                  className={
                    "text-[10px] "
                    + "font-bold "
                    + "uppercase "
                    + "tracking-[0.16em] "
                    + "text-slate-400"
                  }
                >
                  Order context
                </p>

                <span
                  className={
                    "text-[10px] "
                    + "text-slate-400"
                  }
                >
                  {
                    ticket.orders.length
                  }
                </span>
              </div>

              {
                ticket.orders.length
                === 0
                ? (
                  <p
                    className={
                      "mt-3 text-xs "
                      + "leading-5 "
                      + "text-slate-500"
                    }
                  >
                    No verified order context
                    is attached.
                  </p>
                )
                : (
                  <div
                    className={
                      "mt-3 space-y-3"
                    }
                  >
                    {
                      ticket.orders.map(
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
                                  "text-xs "
                                  + "font-semibold"
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
                                  + "text-[9px] "
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
                                "mt-2 text-[10px] "
                                + "leading-5 "
                                + "text-slate-500"
                              }
                            >
                              {
                                summarizeRecord(
                                  order
                                    .fulfillment_summary,
                                )
                              }
                            </p>

                            <p
                              className={
                                "mt-1 text-[10px] "
                                + "leading-5 "
                                + "text-slate-500"
                              }
                            >
                              {
                                summarizeRecord(
                                  order
                                    .total_summary,
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
                "rounded-2xl "
                + "border "
                + "border-slate-200 "
                + "bg-white "
                + "p-4 "
                + "shadow-sm"
              }
            >
              <p
                className={
                  "text-[10px] "
                  + "font-bold "
                  + "uppercase "
                  + "tracking-[0.16em] "
                  + "text-slate-400"
                }
              >
                Ticket actions
              </p>

              <button
                type="button"
                disabled={
                  actionBusy
                    !== null
                }
                onClick={
                  () =>
                    void assignSelf()
                }
                className={
                  "mt-3 w-full "
                  + "rounded-xl "
                  + "border "
                  + "border-slate-200 "
                  + "px-3 py-2.5 "
                  + "text-xs "
                  + "font-semibold "
                  + "text-slate-700 "
                  + "transition "
                  + "hover:bg-slate-50 "
                  + "disabled:opacity-40"
                }
              >
                {
                  actionBusy
                  === "assign"
                    ? "Assigning..."
                    : "Assign to me"
                }
              </button>

              <details
                className={
                  "mt-3 "
                  + "rounded-xl "
                  + "border "
                  + "border-amber-200 "
                  + "bg-amber-50"
                }
              >
                <summary
                  className={
                    "cursor-pointer "
                    + "px-3 py-2.5 "
                    + "text-xs "
                    + "font-semibold "
                    + "text-amber-900"
                  }
                >
                  Escalate
                </summary>

                <div
                  className={
                    "border-t "
                    + "border-amber-200 "
                    + "p-3"
                  }
                >
                  <textarea
                    value={
                      escalationReason
                    }
                    onChange={
                      (event) =>
                        setEscalationReason(
                          event
                            .target
                            .value,
                        )
                    }
                    rows={3}
                    placeholder={
                      "Why does this need review?"
                    }
                    className={
                      "w-full resize-none "
                      + "rounded-lg "
                      + "border "
                      + "border-amber-200 "
                      + "bg-white "
                      + "px-3 py-2 "
                      + "text-xs "
                      + "outline-none"
                    }
                  />

                  <select
                    value={
                      escalationPriority
                    }
                    onChange={
                      (event) =>
                        setEscalationPriority(
                          event
                            .target
                            .value as
                            TicketPriority,
                        )
                    }
                    className={
                      "mt-2 w-full "
                      + "rounded-lg "
                      + "border "
                      + "border-amber-200 "
                      + "bg-white "
                      + "px-3 py-2 "
                      + "text-xs"
                    }
                  >
                    <option value="P1">
                      P1 - Urgent
                    </option>
                    <option value="P2">
                      P2 - High
                    </option>
                    <option value="P3">
                      P3 - Normal
                    </option>
                    <option value="P4">
                      P4 - Low
                    </option>
                  </select>

                  <button
                    type="button"
                    disabled={
                      actionBusy
                        !== null
                      ||
                      !escalationReason
                        .trim()
                    }
                    onClick={
                      () =>
                        void escalate()
                    }
                    className={
                      "mt-2 w-full "
                      + "rounded-lg "
                      + "bg-amber-700 "
                      + "px-3 py-2 "
                      + "text-xs "
                      + "font-semibold "
                      + "text-white "
                      + "disabled:opacity-40"
                    }
                  >
                    {
                      actionBusy
                      === "escalate"
                        ? "Escalating..."
                        : "Confirm escalation"
                    }
                  </button>
                </div>
              </details>

              <details
                className={
                  "mt-3 "
                  + "rounded-xl "
                  + "border "
                  + "border-slate-200"
                }
              >
                <summary
                  className={
                    "cursor-pointer "
                    + "px-3 py-2.5 "
                    + "text-xs "
                    + "font-semibold "
                    + "text-slate-700"
                  }
                >
                  Resolve ticket
                </summary>

                <div
                  className={
                    "border-t "
                    + "border-slate-200 "
                    + "p-3"
                  }
                >
                  <select
                    value={
                      resolutionCode
                    }
                    onChange={
                      (event) =>
                        setResolutionCode(
                          event
                            .target
                            .value as
                            AgentResolutionCode,
                        )
                    }
                    className={
                      "w-full rounded-lg "
                      + "border "
                      + "border-slate-200 "
                      + "bg-white "
                      + "px-3 py-2 "
                      + "text-xs"
                    }
                  >
                    {
                      RESOLUTION_OPTIONS
                        .map(
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

                  <button
                    type="button"
                    disabled={
                      actionBusy
                        !== null
                    }
                    onClick={
                      () =>
                        void resolve()
                    }
                    className={
                      "mt-2 w-full "
                      + "rounded-lg "
                      + "bg-slate-950 "
                      + "px-3 py-2 "
                      + "text-xs "
                      + "font-semibold "
                      + "text-white "
                      + "disabled:opacity-40"
                    }
                  >
                    {
                      actionBusy
                      === "resolve"
                        ? "Resolving..."
                        : "Resolve ticket"
                    }
                  </button>
                </div>
              </details>
            </section>
          </aside>
        </div>
      </div>
    </StaffShell>
  );
}
