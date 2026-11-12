import type { FieldState } from "../lib/api";
import { cropColor, cropLabel } from "../lib/crops";
import { harvestLine, stageLabel } from "../lib/format";

/** A field with one stage bar per planting, coloured by crop. */
export default function FieldCard({ field }: { field: FieldState }) {
  const meta = [field.area_hectares && `${field.area_hectares} ha`, field.plantings.length > 1 && "intercrop"]
    .filter(Boolean)
    .join(" · ");
  const soonest = field.plantings.filter((p) => p.harvest_start).sort((a, b) => a.harvest_start!.localeCompare(b.harvest_start!))[0];
  const harvest = soonest ? harvestLine(soonest.harvest_start, soonest.harvest_end) : null;

  return (
    <div className="flex animate-rise flex-col gap-4 rounded-lg bg-raised p-5">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-h3">{field.name}</span>
        {meta && <span className="text-small text-ink-muted">{meta}</span>}
      </div>
      {field.plantings.length === 0 && <span className="text-small text-ink-muted">Nothing planted in this field.</span>}
      {field.plantings.map((p) => (
        <div key={p.id} className="flex flex-col gap-2">
          <div className="flex items-center justify-between gap-2 text-small">
            <span className="inline-flex items-center gap-2">
              <span aria-hidden className="size-2 rounded-pill" style={{ background: cropColor(p.crop) }} />
              {cropLabel(p.crop)} · {stageLabel(p.stage)}
            </span>
            {p.day !== null && <span className="tabular text-ink-muted">Day {p.day}</span>}
          </div>
          <div
            className="h-2 overflow-hidden rounded-pill bg-ink/5"
            role="progressbar"
            aria-label={`${cropLabel(p.crop)} season`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round((p.progress ?? 0) * 100)}
          >
            <div
              className="h-full origin-left rounded-pill transition-transform duration-700 ease-reveal"
              style={{ background: cropColor(p.crop), transform: `scaleX(${p.progress ?? 0})` }}
            />
          </div>
        </div>
      ))}
      {harvest && <span className="text-small text-ink-muted">{harvest}</span>}
    </div>
  );
}
