import { useState } from "react";
import type { Risk } from "../lib/api";
import { cropLabel } from "../lib/crops";

const DOT = { high: "bg-risk-high", medium: "bg-risk-medium", low: "bg-risk-low" } as const;
const URGENCY = { immediate: "Act now", this_week: "This week", monitor: "Keep an eye on it" } as const;

/** Every risk firing now. Each opens to the rule behind it and the readings that triggered it. */
export default function RiskList({ risks }: { risks: Risk[] }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="flex animate-rise flex-col gap-3 rounded-lg bg-raised p-5">
      <span className="text-h3">Risks</span>
      {risks.length === 0 && (
        <p className="text-small text-ink-muted">No rule is firing for this farm today. Log rain, pests or disease to keep it current.</p>
      )}
      <ul className="flex flex-col gap-2">
        {risks.map((r) => {
          const key = `${r.planting_id}-${r.id}`;
          const isOpen = open === key;
          return (
            <li key={key}>
              <button
                type="button"
                aria-expanded={isOpen}
                onClick={() => setOpen(isOpen ? null : key)}
                className="flex w-full flex-col gap-2 rounded-md bg-surface p-4 text-left transition duration-150 ease-ui hover:bg-ink/5"
              >
                <span className="flex items-start justify-between gap-3">
                  <span className="flex flex-col">
                    <span className="text-body">{r.title}</span>
                    <span className="text-small text-ink-muted">
                      {cropLabel(r.crop)} · {r.field} · {URGENCY[r.urgency]}
                    </span>
                  </span>
                  <span className="inline-flex shrink-0 items-center gap-2 rounded-pill bg-ink px-3 py-1 text-small text-on-ink">
                    <span aria-hidden className={`size-2 rounded-pill ${DOT[r.severity]}`} />
                    {r.severity[0].toUpperCase() + r.severity.slice(1)}
                  </span>
                </span>
                {isOpen && (
                  <span className="flex flex-col gap-2 text-small text-ink-muted">
                    <span>{r.reason}</span>
                    {r.facts.length > 0 && (
                      <span className="flex flex-col">
                        <span className="text-ink">Readings behind it</span>
                        {r.facts.map((f) => (
                          <span key={f}>· {f}</span>
                        ))}
                      </span>
                    )}
                    <span className="text-caption">Rule source: {r.source}</span>
                  </span>
                )}
                {!isOpen && <span className="text-caption text-ink-muted">Show the rule</span>}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
