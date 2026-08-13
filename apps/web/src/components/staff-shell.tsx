"use client";

import type {
  ReactNode,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  getSupabaseBrowserClient,
} from "@/lib/supabase-browser";

type StaffShellProps = {
  active:
    "queue"
    | "operations";
  title: string;
  subtitle: string;
  staffEmail: string;
  children: ReactNode;
  onRefresh?: () => void;
  refreshBusy?: boolean;
};

export default function StaffShell({
  active,
  title,
  subtitle,
  staffEmail,
  children,
  onRefresh,
  refreshBusy = false,
}: StaffShellProps) {
  const router =
    useRouter();

  async function signOut() {
    const supabase =
      getSupabaseBrowserClient();

    await supabase.auth
      .signOut();

    router.replace(
      "/staff/login",
    );
  }

  const navigation = [
    {
      key:
        "queue" as const,
      label:
        "Queue",
      helper:
        "Review and respond",
      path:
        "/staff",
    },
    {
      key:
        "operations" as const,
      label:
        "Operations",
      helper:
        "Health and metrics",
      path:
        "/staff/dashboard",
    },
  ];

  return (
    <div
      className={
        "min-h-screen "
        + "bg-slate-100 "
        + "text-slate-950"
      }
    >
      <div
        className={
          "mx-auto grid "
          + "min-h-screen "
          + "max-w-[1920px] "
          + "lg:grid-cols-[230px_minmax(0,1fr)]"
        }
      >
        <aside
          className={
            "hidden "
            + "border-r border-slate-800 "
            + "bg-slate-950 "
            + "text-white "
            + "lg:sticky lg:top-0 "
            + "lg:flex lg:h-screen "
            + "lg:flex-col"
          }
        >
          <div
            className={
              "border-b "
              + "border-white/10 "
              + "px-5 py-6"
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
                  + "bg-white "
                  + "text-sm "
                  + "font-black "
                  + "text-slate-950"
                }
              >
                SP
              </div>

              <div>
                <p
                  className={
                    "text-[10px] "
                    + "font-semibold "
                    + "uppercase "
                    + "tracking-[0.2em] "
                    + "text-slate-400"
                  }
                >
                  Northstar Commerce
                </p>

                <p
                  className={
                    "mt-1 text-sm "
                    + "font-semibold"
                  }
                >
                  SupportPilot AI
                </p>
              </div>
            </div>
          </div>

          <nav
            className={
              "space-y-2 p-4"
            }
          >
            {navigation.map(
              (item) => {
                const selected =
                  active === item.key;

                return (
                  <button
                    key={
                      item.key
                    }
                    type="button"
                    onClick={
                      () =>
                        router.push(
                          item.path,
                        )
                    }
                    className={[
                      (
                        "w-full "
                        + "rounded-xl "
                        + "px-3 py-3 "
                        + "text-left "
                        + "transition"
                      ),
                      selected
                        ? (
                          "bg-white "
                          + "text-slate-950"
                        )
                        : (
                          "text-slate-300 "
                          + "hover:bg-white/10 "
                          + "hover:text-white"
                        ),
                    ].join(
                      " ",
                    )}
                  >
                    <p
                      className={
                        "text-sm "
                        + "font-semibold"
                      }
                    >
                      {item.label}
                    </p>

                    <p
                      className={[
                        (
                          "mt-0.5 "
                          + "text-[11px]"
                        ),
                        selected
                          ? "text-slate-500"
                          : "text-slate-500",
                      ].join(
                        " ",
                      )}
                    >
                      {item.helper}
                    </p>
                  </button>
                );
              },
            )}
          </nav>

          <div
            className={
              "mt-auto "
              + "border-t "
              + "border-white/10 "
              + "p-4"
            }
          >
            <div
              className={
                "rounded-xl "
                + "bg-white/5 "
                + "p-3"
              }
            >
              <p
                className={
                  "text-[10px] "
                  + "font-semibold "
                  + "uppercase "
                  + "tracking-wide "
                  + "text-slate-500"
                }
              >
                Signed in
              </p>

              <p
                className={
                  "mt-1 truncate "
                  + "text-xs "
                  + "text-slate-300"
                }
              >
                {staffEmail}
              </p>
            </div>

            <button
              type="button"
              onClick={
                () =>
                  void signOut()
              }
              className={
                "mt-3 w-full "
                + "rounded-xl "
                + "border "
                + "border-white/10 "
                + "px-3 py-2.5 "
                + "text-xs "
                + "font-semibold "
                + "text-slate-300 "
                + "transition "
                + "hover:bg-white/10 "
                + "hover:text-white"
              }
            >
              Sign out
            </button>
          </div>
        </aside>

        <div
          className={
            "min-w-0"
          }
        >
          <header
            className={
              "sticky top-0 z-30 "
              + "border-b "
              + "border-slate-200 "
              + "bg-white/95 "
              + "backdrop-blur"
            }
          >
            <div
              className={
                "flex min-h-16 "
                + "items-center "
                + "justify-between "
                + "gap-4 "
                + "px-4 py-3 "
                + "sm:px-5 "
                + "xl:px-6"
              }
            >
              <div
                className={
                  "min-w-0"
                }
              >
                <p
                  className={
                    "truncate "
                    + "text-base "
                    + "font-semibold "
                    + "tracking-tight"
                  }
                >
                  {title}
                </p>

                <p
                  className={
                    "mt-0.5 truncate "
                    + "text-xs "
                    + "text-slate-500"
                  }
                >
                  {subtitle}
                </p>
              </div>

              <div
                className={
                  "flex shrink-0 "
                  + "items-center gap-2"
                }
              >
                {onRefresh && (
                  <button
                    type="button"
                    disabled={
                      refreshBusy
                    }
                    onClick={
                      onRefresh
                    }
                    className={
                      "rounded-xl "
                      + "border "
                      + "border-slate-200 "
                      + "bg-white "
                      + "px-3 py-2 "
                      + "text-xs "
                      + "font-semibold "
                      + "text-slate-700 "
                      + "transition "
                      + "hover:bg-slate-50 "
                      + "disabled:opacity-50"
                    }
                  >
                    {refreshBusy
                      ? "Refreshing..."
                      : "Refresh"}
                  </button>
                )}

                <button
                  type="button"
                  onClick={
                    () =>
                      void signOut()
                  }
                  className={
                    "rounded-xl "
                    + "border "
                    + "border-slate-200 "
                    + "bg-white "
                    + "px-3 py-2 "
                    + "text-xs "
                    + "font-semibold "
                    + "text-slate-700 "
                    + "lg:hidden"
                  }
                >
                  Sign out
                </button>
              </div>
            </div>

            <div
              className={
                "grid grid-cols-2 "
                + "border-t "
                + "border-slate-100 "
                + "lg:hidden"
              }
            >
              {navigation.map(
                (item) => (
                  <button
                    key={
                      item.key
                    }
                    type="button"
                    onClick={
                      () =>
                        router.push(
                          item.path,
                        )
                    }
                    className={[
                      (
                        "px-4 py-2.5 "
                        + "text-xs "
                        + "font-semibold"
                      ),
                      active === item.key
                        ? (
                          "bg-slate-950 "
                          + "text-white"
                        )
                        : (
                          "bg-white "
                          + "text-slate-600"
                        ),
                    ].join(
                      " ",
                    )}
                  >
                    {item.label}
                  </button>
                ),
              )}
            </div>
          </header>

          {children}
        </div>
      </div>
    </div>
  );
}
