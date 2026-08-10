import CustomerChat from "@/components/customer-chat";


export default function Home() {
  return (
    <main className="min-h-screen bg-slate-100 px-5 py-12 sm:px-8">
      <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[1fr_520px] lg:items-center">

        <section>
          <div className="inline-flex rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">
            SupportPilot AI
          </div>

          <h1 className="mt-6 max-w-xl text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
            Support that knows when
            to answer — and when
            to involve a person.
          </h1>

          <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">
            Get help with orders,
            shipping, returns and product
            questions through Northstar
            Commerce support.
          </p>

          <div className="mt-8 grid max-w-xl gap-4 sm:grid-cols-3">
            {[
              "Order support",
              "Policy answers",
              "Human escalation",
            ].map((item) => (
              <div
                key={item}
                className="rounded-2xl border border-slate-200 bg-white p-4 text-sm font-medium text-slate-700"
              >
                {item}
              </div>
            ))}
          </div>
        </section>

        <CustomerChat />

      </div>
    </main>
  );
}