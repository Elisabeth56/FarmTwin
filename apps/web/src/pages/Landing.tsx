import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHealth } from "../lib/api";

type HealthState = "checking" | "ok" | "offline";

export default function Landing() {
  const [health, setHealth] = useState<HealthState>("checking");

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((res) => {
        if (cancelled) return;
        setHealth(res.status === "ok" ? "ok" : "offline");
      })
      .catch(() => {
        if (cancelled) return;
        setHealth("offline");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const statusLabel =
    health === "checking"
      ? "Backend: checking…"
      : health === "ok"
        ? "Backend: OK"
        : "Backend: offline";

  const statusPillCls =
    health === "ok"
      ? "bg-brand-tint text-brand"
      : "bg-raised border border-hairline text-ink-muted";

  const statusDot =
    health === "ok"
      ? "bg-brand"
      : health === "offline"
        ? "bg-ink-faint"
        : "bg-ink-faint";

  return (
    <div className="min-h-screen flex flex-col">
      <header className="px-6 py-5 max-w-6xl mx-auto w-full">
        <span className="text-lead font-semibold text-brand">🌱 FarmTwin</span>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-6 pb-16">
        <section className="w-full max-w-[640px] mx-auto text-center">
          <h1 className="text-h1 md:text-6xl font-semibold tracking-tight leading-[1.05]">
            Know your farm. Predict what's next. Protect your harvest.
          </h1>
          <p className="text-lead text-ink-muted mt-6 max-w-xl mx-auto">
            FarmTwin builds a digital representation of your farm from what you
            tell it and what you observe. It pairs that with local agricultural
            knowledge to help you spot risks early and decide what to do next.
          </p>

          <div className="mt-10">
            <Link
              to="/setup"
              className="inline-block bg-brand text-on-ink hover:bg-brand rounded-md px-8 py-4 text-body font-medium transition-colors"
            >
              Create your farm
            </Link>
            <p className="text-small text-ink-faint mt-3">
              Runs entirely on this laptop — no internet required.
            </p>
          </div>

          <div className="mt-10 flex justify-center">
            <span
              className={`inline-flex items-center gap-2 text-caption rounded-pill px-3 py-1 ${statusPillCls}`}
            >
              <span className={`inline-block h-1.5 w-1.5 rounded-pill ${statusDot}`} />
              {statusLabel}
            </span>
          </div>
        </section>

        <section className="w-full max-w-5xl mx-auto mt-24 grid grid-cols-1 md:grid-cols-3 gap-2">
          <div className="p-6">
            <div className="text-h3">🗺️</div>
            <h3 className="text-body font-semibold mt-3">Add your farm</h3>
            <p className="text-small text-ink-muted mt-2">
              Sketch out your farm's location, fields, and the crops you have in
              the ground. It only takes a minute.
            </p>
          </div>
          <div className="p-6">
            <div className="text-h3">📝</div>
            <h3 className="text-body font-semibold mt-3">Log what you see</h3>
            <p className="text-small text-ink-muted mt-2">
              Record rainfall, humidity, pests, and other observations so
              FarmTwin has the ground truth of your fields.
            </p>
          </div>
          <div className="p-6">
            <div className="text-h3">💬</div>
            <h3 className="text-body font-semibold mt-3">Ask FarmTwin</h3>
            <p className="text-small text-ink-muted mt-2">
              Ask farm-specific questions and get recommendations grounded in
              your data and trusted agronomy sources.
            </p>
          </div>
        </section>
      </main>

      <footer className="text-caption text-ink-faint py-8 text-center">
        Built for the Africa Deep Tech Challenge 2026
      </footer>
    </div>
  );
}
