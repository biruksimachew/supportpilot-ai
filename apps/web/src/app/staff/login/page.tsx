import StaffLoginForm
  from "@/components/staff-login-form";


export default function StaffLoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-5 py-12">

      <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-xl shadow-slate-200/50">

        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            SupportPilot AI
          </p>

          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
            Staff console
          </h1>

          <p className="mt-3 text-sm leading-6 text-slate-500">
            Sign in with an authorized
            Northstar support account.
          </p>
        </div>

        <StaffLoginForm />

      </section>

    </main>
  );
}