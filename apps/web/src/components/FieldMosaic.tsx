import { cropColor, cropLabel } from "../lib/crops";
import type { FarmSummary } from "../lib/api";

/** A farm drawn as its plots: each plot's width follows its share of the field area. */
export default function FieldMosaic({ plots, height = "h-16" }: { plots: FarmSummary["plots"]; height?: string }) {
  if (plots.length === 0) {
    return <div className={`${height} rounded-md bg-ink/5`} aria-hidden />;
  }
  return (
    <div className={`flex ${height} gap-1 overflow-hidden rounded-md`} role="img" aria-label={plots.map((p) => `${cropLabel(p.crop)} in ${p.field}`).join(", ")}>
      {plots.map((p) => (
        <span key={p.planting_id} className="rounded-[6px]" style={{ flex: `${p.share} 1 0`, background: cropColor(p.crop) }} />
      ))}
    </div>
  );
}
