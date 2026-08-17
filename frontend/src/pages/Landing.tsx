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

  const statusDot =
    health === "ok"
      ? "bg-emerald-600"
      : health === "offline"
        ? "bg-stone-400"
        : "bg-amber-500";

  return (
    <main className="min-h-screen bg-stone-50 text-stone-800 flex items-center justify-center px-6">
      <div className="max-w-xl w-full text-center space-y-8">
        <h1 className="text-5xl font-semibold tracking-tight text-emerald-900">
          FarmTwin
        </h1>
        <p className="text-lg text-stone-600">
          A quiet, offline companion for your farm.
        </p>
        <div className="inline-flex items-center gap-2 text-sm text-stone-600 bg-white/60 border border-stone-200 rounded-full px-4 py-1.5">
          <span className={`inline-block h-2 w-2 rounded-full ${statusDot}`} />
          {statusLabel}
        </div>
        <div>
          <Link
            to="/setup"
            className="inline-block bg-emerald-700 hover:bg-emerald-800 text-white font-medium px-6 py-3 rounded-lg transition-colors"
          >
            Create your farm
          </Link>
        </div>
      </div>
    </main>
  );
}
