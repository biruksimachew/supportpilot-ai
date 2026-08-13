"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import StaffShell
  from "@/components/staff-shell";

import {
  getAgentDashboard,
  StaffApiError,
} from "@/lib/staff-api";

import {
  getSupabaseBrowserClient,
} from "@/lib/supabase-browser";

import type {
  AgentDashboardResponse,
  DashboardDistributionItem,
} from "@/lib/staff-types";


function humanize(
  value: string,
): string {
  return value
    .replaceAll(
      "_",
      " ",
    )
    .toLowerCase()
    .replace(
      /\b\w/g,
      (character) =>
        character.toUpperCase(),
    );
}


function relativeTime(
  value: string,
): string {
  const timestamp =
    new Date(value)
      .getTime();

  const difference =
    Date.now()
    - timestamp;

  if (
    !Number.isFinite(
      timestamp,
    )
  ) {
    return "Unknown";
  }

  const minutes =
    Math.max(
      0,
      Math.floor(
        difference
        / 60000,
      ),
    );

  if (minutes < 1) {
    return "Just now";
  }

  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours =
    Math.floor(
      minutes / 60,
    );

  if (hours < 24) {
    return `${hours}h ago`;
  }

  const days =
    Math.floor(
      hours / 24,
    );

  return `${days}d ago`;
}


function percentageLabel(
  value:
    number | null,
): string {
  if (value === null) {
    return "-";
  }

  return `${value.toFixed(1)}%`;
}


function MetricCard({
  label,
  value,
  helper,
  attention = false,
}: {
  label: string;
  value:
    string | number;
  helper: string;
  attention?: boolean;
}) {
  return (
    <article
      className={[
        (
          "rounded-2xl "
          + "border p-5 "
          + "shadow-sm"
        ),
        attention
          ? (
            "border-amber-200 "
            + "bg-amber-50"
          )
          : (
            "border-slate-200 "
            + "bg-white"
          ),
      ].join(
        " ",
      )}
    >
      <p
        className={[
          (
            "text-[10px] "
            + "font-bold "
            + "uppercase "
            + "tracking-[0.16em]"
          ),
          attention
            ? "text-amber-700"
            : "text-slate-400",
        ].join(
          " ",
        )}
      >
        {label}
      </p>

      <p
        className={
          "mt-3 text-3xl "
          + "font-semibold "
          + "tracking-tight "
          + "text-slate-950"
        }
      >
        {value}
      </p>

      <p
        className={[
          (
            "mt-2 text-xs"
          ),
          attention
            ? "text-amber-800"
            : "text-slate-500",
        ].join(
          " ",
        )}
      >
        {helper}
      </p>
    </article>
  );
}


function DistributionPanel({
  title,
  subtitle,
  items,
}: {
  title: string;
  subtitle?: string;
  items: DashboardDistributionItem[];
}) {
  const maximum =
    Math.max(
      1,
      ...items.map(
        (item) =>
          item.count,
      ),
    );

  return (
    <section
      className={
        "rounded-2xl "
        + "border "
        + "border-slate-200 "
        + "bg-white p-5 "
        + "shadow-sm"
      }
    >
      <div>
        <h2
          className={
            "text-sm "
            + "font-semibold "
            + "text-slate-900"
          }
        >
          {title}
        </h2>

        {subtitle && (
          <p
            className={
              "mt-1 text-xs "
              + "text-slate-400"
            }
          >
            {subtitle}
          </p>
        )}
      </div>

      <div
        className={
          "mt-5 space-y-4"
        }
      >
        {items.map(
          (item) => {
            const width =
              Math.max(
                4,
                (
                  item.count
                  / maximum
                )
                * 100,
              );

            return (
              <div
                key={
                  item.key
                }
              >
                <div
                  className={
                    "flex items-center "
                    + "justify-between "
                    + "gap-3"
                  }
                >
                  <span
                    className={
                      "text-xs "
                      + "font-medium "
                      + "text-slate-600"
                    }
                  >
                    {
                      humanize(
                        item.key,
                      )
                    }
                  </span>

                  <span
                    className={
                      "text-xs "
                      + "font-semibold "
                      + "text-slate-900"
                    }
                  >
                    {item.count}
                  </span>
                </div>

                <div
                  className={
                    "mt-2 h-2 "
                    + "overflow-hidden "
                    + "rounded-full "
                    + "bg-slate-100"
                  }
                >
                  <div
                    className={
                      "h-full "
                      + "rounded-full "
                      + "bg-slate-950"
                    }
                    style={{
                      width:
                        `${width}%`,
                    }}
                  />
                </div>
              </div>
            );
          },
        )}

        {items.length === 0 && (
          <div
            className={
              "rounded-xl "
              + "bg-slate-50 "
              + "px-4 py-6 "
              + "text-center "
              + "text-xs "
              + "text-slate-500"
            }
          >
            No activity recorded yet.
          </div>
        )}
      </div>
    </section>
  );
}


export default function OperationsDashboard() {
  const router =
    useRouter();

  const [
    dashboard,
    setDashboard,
  ] =
    useState<
      AgentDashboardResponse | null
    >(null);

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
    loading,
    setLoading,
  ] =
    useState(true);

  const [
    refreshing,
    setRefreshing,
  ] =
    useState(false);

  const [
    error,
    setError,
  ] =
    useState<
      string | null
    >(null);


  const loadDashboard =
    useCallback(
      async (
        token: string,
      ) => {
        const result =
          await getAgentDashboard(
            token,
          );

        setDashboard(
          result,
        );

        setError(
          null,
        );
      },
      [],
    );


  useEffect(() => {
    let active =
      true;

    async function load() {
      const supabase =
        getSupabaseBrowserClient();

      try {
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

        if (!active) {
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

        await loadDashboard(
          data.session
            .access_token,
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
          await supabase.auth
            .signOut();

          router.replace(
            "/staff/login",
          );
          return;
        }

        if (active) {
          setError(
            "Operations metrics could not be loaded.",
          );
        }
      } finally {
        if (active) {
          setLoading(
            false,
          );
        }
      }
    }

    void load();

    return () => {
      active = false;
    };
  }, [
    loadDashboard,
    router,
  ]);


  async function refresh() {
    if (!accessToken) {
      return;
    }

    setRefreshing(
      true,
    );

    try {
      await loadDashboard(
        accessToken,
      );
    } catch (caught) {
      if (
        caught
        instanceof StaffApiError
      ) {
        setError(
          caught.message,
        );
      } else {
        setError(
          "Operations metrics could not be refreshed.",
        );
      }
    } finally {
      setRefreshing(
        false,
      );
    }
  }


  if (loading) {
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
        Loading operations...
      </div>
    );
  }


  if (
    error
    &&
    !dashboard
  ) {
    return (
      <main
        className={
          "flex min-h-screen "
          + "items-center "
          + "justify-center "
          + "bg-slate-100 p-6"
        }
      >
        <div
          className={
            "max-w-md "
            + "rounded-2xl "
            + "border "
            + "border-red-200 "
            + "bg-white p-6 "
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
            Dashboard unavailable
          </p>

          <p
            className={
              "mt-2 text-sm "
              + "text-slate-500"
            }
          >
            {error}
          </p>

          <a
            href="/staff"
            className={
              "mt-5 inline-block "
              + "rounded-xl "
              + "bg-slate-950 "
              + "px-4 py-2 "
              + "text-sm "
              + "font-medium "
              + "text-white"
            }
          >
            Back to queue
          </a>
        </div>
      </main>
    );
  }


  if (!dashboard) {
    return null;
  }


  const queue =
    dashboard.queue;


  return (
    <StaffShell
      active="operations"
      title="Operations dashboard"
      subtitle={
        (
          "Support health · updated "
          + relativeTime(
              dashboard
                .generated_at,
            )
        )
      }
      staffEmail={
        staffEmail
      }
      onRefresh={
        () =>
          void refresh()
      }
      refreshBusy={
        refreshing
      }
    >
      <div
        className={
          "space-y-5 "
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
              + "border "
              + "border-red-200 "
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
            "grid gap-3 "
            + "sm:grid-cols-2 "
            + "2xl:grid-cols-4"
          }
        >
          <MetricCard
            label="Open tickets"
            value={
              queue.open_tickets
            }
            helper={
              (
                queue.unassigned
                + " unassigned · "
                + queue.new_tickets
                + " new"
              )
            }
          />

          <MetricCard
            label="Needs review"
            value={
              queue.review_required
            }
            helper={
              (
                queue.urgent_p1_p2
                + " P1/P2 open"
              )
            }
            attention={
              queue.review_required
              > 0
            }
          />

          <MetricCard
            label="Waiting customer"
            value={
              queue.waiting_customer
            }
            helper={
              (
                queue.drafted
                + " drafted replies"
              )
            }
          />

          <MetricCard
            label="Restricted open"
            value={
              queue.restricted_open
            }
            helper={
              "Human control required"
            }
            attention={
              queue.restricted_open
              > 0
            }
          />
        </section>

        <section
          className={
            "grid gap-3 "
            + "lg:grid-cols-3"
          }
        >
          <MetricCard
            label="AI automation eligibility"
            value={
              percentageLabel(
                dashboard
                  .ai
                  .automation_rate_pct,
              )
            }
            helper={
              dashboard
                .ai
                .total_runs
              === 0
                ? "No evaluated AI runs yet"
                : (
                  dashboard
                    .ai
                    .auto_respond
                  + " of "
                  + dashboard
                      .ai
                      .total_runs
                  + " runs eligible"
                )
            }
          />

          <MetricCard
            label="Delivery success"
            value={
              percentageLabel(
                dashboard
                  .delivery
                  .delivery_success_rate_pct,
              )
            }
            helper={
              (
                dashboard
                  .delivery
                  .delivered
                + " delivered · "
                + dashboard
                    .delivery
                    .failed
                + " failed · "
                + dashboard
                    .delivery
                    .uncertain
                + " uncertain"
              )
            }
            attention={
              (
                dashboard
                  .delivery
                  .failed
                +
                dashboard
                  .delivery
                  .uncertain
              )
              > 0
            }
          />

          <MetricCard
            label="Resolved tickets"
            value={
              dashboard
                .resolution
                .resolved_tickets
            }
            helper={
              dashboard
                .resolution
                .average_resolution_minutes
              === null
                ? "No resolution timing yet"
                : (
                  dashboard
                    .resolution
                    .average_resolution_minutes
                  + " min average"
                )
            }
          />
        </section>

        <section
          className={
            "grid gap-4 "
            + "lg:grid-cols-2 "
            + "2xl:grid-cols-3"
          }
        >
          <DistributionPanel
            title="Queue by status"
            subtitle="Current ticket lifecycle"
            items={
              dashboard
                .status_breakdown
            }
          />

          <DistributionPanel
            title="Open priorities"
            subtitle="Unresolved workload"
            items={
              dashboard
                .priority_breakdown
            }
          />

          <DistributionPanel
            title="Open channels"
            subtitle="Chat and email mix"
            items={
              dashboard
                .channel_breakdown
            }
          />

          <DistributionPanel
            title="Intent mix"
            subtitle="Current support demand"
            items={
              dashboard
                .intent_breakdown
            }
          />

          <DistributionPanel
            title="Escalation causes"
            subtitle="Why humans are needed"
            items={
              dashboard
                .escalation_breakdown
            }
          />

          <section
            className={
              "rounded-2xl "
              + "border "
              + "border-slate-200 "
              + "bg-white p-5 "
              + "shadow-sm"
            }
          >
            <h2
              className={
                "text-sm "
                + "font-semibold "
                + "text-slate-900"
              }
            >
              AI decision health
            </h2>

            <p
              className={
                "mt-1 text-xs "
                + "text-slate-400"
              }
            >
              Persisted decision outcomes
            </p>

            <div
              className={
                "mt-5 space-y-2"
              }
            >
              {[
                [
                  "Auto respond",
                  dashboard
                    .ai
                    .auto_respond,
                ],
                [
                  "Human review",
                  dashboard
                    .ai
                    .review_required,
                ],
                [
                  "Clarification",
                  dashboard
                    .ai
                    .request_clarification,
                ],
                [
                  "Failed",
                  dashboard
                    .ai
                    .failed,
                ],
              ].map(
                (
                  [
                    label,
                    value,
                  ],
                ) => (
                  <div
                    key={
                      label
                    }
                    className={
                      "flex "
                      + "items-center "
                      + "justify-between "
                      + "rounded-xl "
                      + "bg-slate-50 "
                      + "px-3 py-3"
                    }
                  >
                    <span
                      className={
                        "text-xs "
                        + "text-slate-600"
                      }
                    >
                      {label}
                    </span>

                    <span
                      className={
                        "text-sm "
                        + "font-semibold"
                      }
                    >
                      {value}
                    </span>
                  </div>
                ),
              )}
            </div>

            {
              dashboard
                .ai
                .total_runs
              === 0
              &&
              (
                <div
                  className={
                    "mt-4 "
                    + "rounded-xl "
                    + "border "
                    + "border-dashed "
                    + "border-slate-200 "
                    + "px-3 py-3 "
                    + "text-[10px] "
                    + "leading-5 "
                    + "text-slate-500"
                  }
                >
                  Empty by design:
                  no evaluated AI runs
                  are currently persisted.
                  The dashboard does not
                  fabricate an automation
                  percentage.
                </div>
              )
            }
          </section>
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
              "flex items-center "
              + "justify-between "
              + "gap-3 "
              + "border-b "
              + "border-slate-200 "
              + "px-5 py-4"
            }
          >
            <div>
              <h2
                className={
                  "text-sm "
                  + "font-semibold "
                  + "text-slate-900"
                }
              >
                Recent operational activity
              </h2>

              <p
                className={
                  "mt-1 text-xs "
                  + "text-slate-400"
                }
              >
                Auditable ticket events
              </p>
            </div>

            <span
              className={
                "rounded-full "
                + "bg-slate-100 "
                + "px-2.5 py-1 "
                + "text-[10px] "
                + "font-semibold "
                + "text-slate-600"
              }
            >
              {
                dashboard
                  .recent_activity
                  .length
              }
            </span>
          </div>

          <div
            className={
              "divide-y "
              + "divide-slate-100"
            }
          >
            {dashboard
              .recent_activity
              .map(
                (activity) => (
                  <div
                    key={
                      activity.id
                    }
                    className={
                      "flex flex-wrap "
                      + "items-center "
                      + "justify-between "
                      + "gap-3 "
                      + "px-5 py-4"
                    }
                  >
                    <div>
                      <p
                        className={
                          "text-sm "
                          + "font-medium "
                          + "text-slate-800"
                        }
                      >
                        {
                          humanize(
                            activity
                              .event_type,
                          )
                        }
                      </p>

                      <p
                        className={
                          "mt-1 text-xs "
                          + "text-slate-400"
                        }
                      >
                        {
                          activity
                            .ticket_reference
                          ?? "Ticket"
                        }
                        {" · "}
                        {
                          humanize(
                            activity
                              .actor_type,
                          )
                        }
                      </p>
                    </div>

                    <span
                      className={
                        "text-xs "
                        + "text-slate-400"
                      }
                    >
                      {
                        relativeTime(
                          activity
                            .created_at,
                        )
                      }
                    </span>
                  </div>
                ),
              )}

            {
              dashboard
                .recent_activity
                .length
              === 0
              &&
              (
                <div
                  className={
                    "px-5 py-10 "
                    + "text-center "
                    + "text-sm "
                    + "text-slate-500"
                  }
                >
                  No recent operational
                  activity recorded.
                </div>
              )
            }
          </div>
        </section>
      </div>
    </StaffShell>
  );
}
