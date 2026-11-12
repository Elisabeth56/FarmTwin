import type { FarmDashboardData } from "../lib/api";
import { shortDate } from "../lib/format";

/** Fourteen daily bars of rainfall. Days with no reading show as a faint stub, not as zero. */
export default function RainChart({ days }: { days: FarmDashboardData["rainfall"] }) {
  const total = days.reduce((sum, d) => sum + (d.mm ?? 0), 0);
  const top = Math.max(10, ...days.map((d) => d.mm ?? 0));
  const recorded = days.filter((d) => d.mm !== null);
  const label = recorded.length
    ? `Rainfall over the last 14 days: ${recorded.map((d) => `${shortDate(d.day)} ${d.mm} mm`).join(", ")}`
    : "No rainfall recorded in the last 14 days";

  return (
    <div className="flex animate-rise flex-col gap-4 rounded-lg bg-raised p-5">
      <div className="flex items-baseline justify-between">
        <span className="text-h3">Rainfall</span>
        <span className="tabular text-small text-ink-muted">Last 14 days · {Math.round(total)} mm</span>
      </div>
      <div role="img" aria-label={label} className="flex h-28 items-end gap-1">
        {days.map((d) => (
          <span
            key={d.day}
            title={d.mm === null ? `${shortDate(d.day)}: no reading` : `${shortDate(d.day)}: ${d.mm} mm`}
            className={`flex-1 rounded-t-[4px] transition-[height] duration-700 ease-reveal ${d.mm === null ? "bg-ink/5" : "bg-crop-rice"}`}
            style={{ height: d.mm === null ? "4px" : `${Math.max(4, (d.mm / top) * 100)}%` }}
          />
        ))}
      </div>
      <div className="flex justify-between text-caption text-ink-muted">
        <span>2 weeks ago</span>
        <span>Today</span>
      </div>
    </div>
  );
}
