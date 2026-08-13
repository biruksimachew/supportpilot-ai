"use client";

import {
  useEffect,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

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
    new Date(
      value,
    ).getTime();

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


function DistributionPanel({
  title,
  items,
}: {
  title: string;
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
        + "border border-slate-200 "
        + "bg-white p-5 "
        + "shadow-sm"
      }
    >

      <h2
        className={
          "text-sm font-semibold "
          + "text-slate-900"
        }
      >
        {title}
      </h2>


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
                      "text-xs font-medium "
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
                      "text-xs font-semibold "
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
                      "h-full rounded-full "
                      + "bg-slate-900"
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
          <p
            className={
              "text-sm "
              + "text-slate-500"
            }
          >
            No activity recorded yet.
          </p>
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
    loading,
    setLoading,
  ] =
    useState(
      true,
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


        setStaffEmail(
          data.session
            .user
            .email
          ?? "",
        );


        const result =
          await getAgentDashboard(
            data.session
              .access_token,
          );


        if (!active) {
          return;
        }


        setDashboard(
          result,
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
            (
              "Operations metrics "
              + "could not be loaded."
            ),
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
    router,
  ]);


  async function logout() {

    const supabase =
      getSupabaseBrowserClient();


    await supabase.auth
      .signOut();


    router.replace(
      "/staff/login",
    );
  }


  if (loading) {

    return (
      <div
        className={
          "flex min-h-screen "
          + "items-center "
          + "justify-center "
          + "bg-slate-50 "
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
    ||
    !dashboard
  ) {

    return (
      <main
        className={
          "flex min-h-screen "
          + "items-center "
          + "justify-center "
          + "bg-slate-50 p-6"
        }
      >

        <div
          className={
            "max-w-md "
            + "rounded-2xl "
            + "border border-red-200 "
            + "bg-white p-6 "
            + "text-center shadow-sm"
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
            {
              error
              ?? "No dashboard data returned."
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
              + "px-4 py-2 "
              + "text-sm font-medium "
              + "text-white"
            }
          >
            Back to queue
          </button>

        </div>

      </main>
    );
  }


  const queue =
    dashboard.queue;


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
            + "max-w-375 "
            + "items-center "
            + "justify-between "
            + "gap-5 px-5 py-4 "
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
                  + "font-semibold"
                }
              >
                Operations
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

              onClick={
                () =>
                  router.push(
                    "/staff",
                  )
              }

              className={
                "rounded-xl "
                + "border border-slate-200 "
                + "bg-white "
                + "px-4 py-2 "
                + "text-sm font-medium "
                + "text-slate-700 "
                + "hover:bg-slate-50"
              }
            >
              Queue
            </button>


            <div
              className={
                "hidden text-right "
                + "md:block"
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
                  + "max-w-60 truncate "
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
                + "hover:bg-slate-50"
              }
            >
              Sign out
            </button>

          </div>

        </div>

      </header>


      <div
        className={
          "mx-auto "
          + "max-w-375 "
          + "space-y-6 "
          + "px-5 py-6 "
          + "lg:px-7"
        }
      >

        <div>

          <p
            className={
              "text-xs font-semibold "
              + "uppercase "
              + "tracking-[0.16em] "
              + "text-slate-400"
            }
          >
            Operations snapshot
          </p>


          <div
            className={
              "mt-1 flex "
              + "flex-wrap "
              + "items-end "
              + "justify-between "
              + "gap-3"
            }
          >

            <h2
              className={
                "text-2xl font-semibold "
                + "tracking-tight"
              }
            >
              Support health
            </h2>


            <p
              className={
                "text-xs "
                + "text-slate-400"
              }
            >
              Updated {
                relativeTime(
                  dashboard
                    .generated_at,
                )
              }
            </p>

          </div>

        </div>


        <section
          className={
            "grid gap-3 "
            + "sm:grid-cols-2 "
            + "xl:grid-cols-4"
          }
        >

          {
            [
              {
                label:
                  "Open tickets",

                value:
                  queue.open_tickets,

                helper:
                  `${queue.unassigned} unassigned`,
              },

              {
                label:
                  "Needs review",

                value:
                  queue.review_required,

                helper:
                  `${queue.urgent_p1_p2} P1/P2 open`,
              },

              {
                label:
                  "Waiting customer",

                value:
                  queue.waiting_customer,

                helper:
                  `${queue.drafted} drafted`,
              },

              {
                label:
                  "Restricted open",

                value:
                  queue.restricted_open,

                helper:
                  "Human control required",
              },
            ].map(
              (metric) => (
                <article
                  key={
                    metric.label
                  }

                  className={
                    "rounded-2xl "
                    + "border border-slate-200 "
                    + "bg-white p-5 "
                    + "shadow-sm"
                  }
                >

                  <p
                    className={
                      "text-xs font-medium "
                      + "text-slate-500"
                    }
                  >
                    {metric.label}
                  </p>


                  <p
                    className={
                      "mt-3 text-3xl "
                      + "font-semibold "
                      + "tracking-tight"
                    }
                  >
                    {metric.value}
                  </p>


                  <p
                    className={
                      "mt-2 text-xs "
                      + "text-slate-400"
                    }
                  >
                    {metric.helper}
                  </p>

                </article>
              ),
            )
          }

        </section>


        <section
          className={
            "grid gap-3 "
            + "lg:grid-cols-3"
          }
        >

          <article
            className={
              "rounded-2xl "
              + "border border-slate-200 "
              + "bg-white p-5 "
              + "shadow-sm"
            }
          >

            <p
              className={
                "text-xs font-medium "
                + "text-slate-500"
              }
            >
              AI automation eligibility
            </p>


            <p
              className={
                "mt-3 text-3xl "
                + "font-semibold"
              }
            >
              {
                percentageLabel(
                  dashboard
                    .ai
                    .automation_rate_pct,
                )
              }
            </p>


            <p
              className={
                "mt-2 text-xs "
                + "text-slate-400"
              }
            >
              {
                dashboard
                  .ai
                  .total_runs
                === 0
                  ? (
                    "No evaluated AI "
                    + "runs yet"
                  )
                  : (
                    dashboard.ai.auto_respond
                    + " of "
                    + dashboard.ai.total_runs
                    + " runs eligible"
                  )
              }
            </p>

          </article>


          <article
            className={
              "rounded-2xl "
              + "border border-slate-200 "
              + "bg-white p-5 "
              + "shadow-sm"
            }
          >

            <p
              className={
                "text-xs font-medium "
                + "text-slate-500"
              }
            >
              Delivery success
            </p>


            <p
              className={
                "mt-3 text-3xl "
                + "font-semibold"
              }
            >
              {
                percentageLabel(
                  dashboard
                    .delivery
                    .delivery_success_rate_pct,
                )
              }
            </p>


            <p
              className={
                "mt-2 text-xs "
                + "text-slate-400"
              }
            >
              {
                dashboard
                  .delivery
                  .delivered
              }
              {" delivered / "}
              {
                dashboard
                  .delivery
                  .total_deliveries
              }
              {" attempts"}
            </p>

          </article>


          <article
            className={
              "rounded-2xl "
              + "border border-slate-200 "
              + "bg-white p-5 "
              + "shadow-sm"
            }
          >

            <p
              className={
                "text-xs font-medium "
                + "text-slate-500"
              }
            >
              Resolved tickets
            </p>


            <p
              className={
                "mt-3 text-3xl "
                + "font-semibold"
              }
            >
              {
                dashboard
                  .resolution
                  .resolved_tickets
              }
            </p>


            <p
              className={
                "mt-2 text-xs "
                + "text-slate-400"
              }
            >
              {
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
            </p>

          </article>

        </section>


        <section
          className={
            "grid gap-4 "
            + "lg:grid-cols-2 "
            + "xl:grid-cols-3"
          }
        >

          <DistributionPanel
            title="Queue by status"

            items={
              dashboard
                .status_breakdown
            }
          />


          <DistributionPanel
            title="Open priorities"

            items={
              dashboard
                .priority_breakdown
            }
          />


          <DistributionPanel
            title="Open channels"

            items={
              dashboard
                .channel_breakdown
            }
          />


          <DistributionPanel
            title="Intent mix"

            items={
              dashboard
                .intent_breakdown
            }
          />


          <DistributionPanel
            title="Escalation causes"

            items={
              dashboard
                .escalation_breakdown
            }
          />


          <section
            className={
              "rounded-2xl "
              + "border border-slate-200 "
              + "bg-white p-5 "
              + "shadow-sm"
            }
          >

            <h2
              className={
                "text-sm font-semibold "
                + "text-slate-900"
              }
            >
              AI decision health
            </h2>


            <div
              className={
                "mt-5 space-y-3"
              }
            >

              {
                [
                  [
                    "Auto respond",
                    dashboard.ai.auto_respond,
                  ],

                  [
                    "Human review",
                    dashboard.ai.review_required,
                  ],

                  [
                    "Clarification",
                    dashboard.ai.request_clarification,
                  ],

                  [
                    "Failed",
                    dashboard.ai.failed,
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
                        "flex items-center "
                        + "justify-between "
                        + "rounded-xl "
                        + "bg-slate-50 "
                        + "px-3 py-2.5"
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
                          "text-sm font-semibold"
                        }
                      >
                        {value}
                      </span>

                    </div>
                  ),
                )
              }

            </div>

          </section>

        </section>


        <section
          className={
            "rounded-2xl "
            + "border border-slate-200 "
            + "bg-white "
            + "shadow-sm"
          }
        >

          <div
            className={
              "border-b "
              + "border-slate-200 "
              + "px-5 py-4"
            }
          >

            <h2
              className={
                "text-sm font-semibold "
                + "text-slate-900"
              }
            >
              Recent operational activity
            </h2>

          </div>


          <div
            className={
              "divide-y "
              + "divide-slate-100"
            }
          >

            {
              dashboard
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
                            "text-sm font-medium "
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
                          {" / "}
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
                )
            }


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

    </main>
  );
}