import { useEffect, useRef, useState } from "react";
import type { Twin } from "@farmtwin/twin";
import type { FieldState, Risk } from "../lib/api";
import { cropLabel } from "../lib/crops";

/** How many plantings the 3D farm has room for; the rest are listed in the field cards. */
const SLOTS = 6;

const SEVERITY_COLOR = { high: "var(--risk-high)", medium: "var(--risk-medium)", low: "var(--risk-low)" } as const;

/** This farm's own plantings drawn as a 3D farm you can turn. Three.js loads only when this mounts. */
export default function FarmTwin3D({ fields, risks, wet }: { fields: FieldState[]; risks: Risk[]; wet: boolean }) {
  const frame = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const badge = useRef<HTMLDivElement>(null);
  const chip = useRef<HTMLDivElement>(null);
  const chipDot = useRef<HTMLSpanElement>(null);
  const chipText = useRef<HTMLSpanElement>(null);
  const twin = useRef<Twin | null>(null);
  const [ready, setReady] = useState(false);

  const drawn = fields.flatMap((f) => f.plantings.map((p) => ({ id: p.id, crop: p.crop, label: `${cropLabel(p.crop)} · ${f.name}` }))).slice(0, SLOTS);
  // the badge points at the most urgent risk that has a plot on screen
  const risk = risks.find((r) => drawn.some((d) => d.id === r.planting_id));
  const badgePlot = risk ? drawn.findIndex((d) => d.id === risk.planting_id) : 0;
  const key = drawn.map((d) => `${d.id}:${d.crop}`).join(",") + `|${badgePlot}`;

  // the scene is rebuilt only when the plots or the badge's plot change
  useEffect(() => {
    let cancelled = false;
    setReady(false);
    void import("@farmtwin/twin").then(({ mountTwin }) => {
      if (cancelled || !frame.current) return;
      twin.current = mountTwin({
        frame: frame.current,
        canvas: canvas.current!,
        badge: badge.current!,
        chip: chip.current!,
        chipDot: chipDot.current!,
        chipText: chipText.current!,
        plots: drawn,
        badgePlot,
        autoRotate: false,
        onDemand: true,
        onReady: () => setReady(true),
      });
    });
    return () => {
      cancelled = true;
      twin.current?.dispose();
      twin.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    if (ready) twin.current?.setRain(wet);
  }, [ready, wet]);

  const extra = fields.reduce((n, f) => n + f.plantings.length, 0) - drawn.length;

  return (
    <div ref={frame} className="relative aspect-[16/7] w-full select-none">
      <canvas
        ref={canvas}
        aria-label={`3D view of this farm: ${drawn.map((d) => d.label).join(", ")}. Drag to turn it.`}
        className={`absolute inset-0 h-full w-full cursor-grab transition-opacity duration-700 active:cursor-grabbing ${ready ? "opacity-100" : "opacity-0"}`}
      />
      {!ready && <div aria-busy="true" aria-label="Loading 3D view" className="absolute inset-0 animate-pulse bg-ink/5" />}

      <div ref={badge} className={`pointer-events-none absolute top-0 left-0 z-10 flex flex-col items-center transition-opacity ${ready && risk ? "opacity-100" : "opacity-0"}`}>
        {risk && (
          <span className="inline-flex items-center gap-2 rounded-pill bg-ink px-3.5 py-2 text-small whitespace-nowrap text-on-ink">
            <span className="size-2 rounded-pill" style={{ background: SEVERITY_COLOR[risk.severity] }} />
            {risk.title} · {risk.severity}
          </span>
        )}
        <span className="h-11 border-l-2 border-dashed border-ink" />
      </div>

      <div ref={chip} className="pointer-events-none absolute top-0 left-0 z-10 hidden items-center gap-1.5 rounded-pill bg-raised px-3 py-1.5 text-small whitespace-nowrap shadow-float">
        <span ref={chipDot} className="size-2 rounded-pill" />
        <span ref={chipText} />
      </div>

      {extra > 0 && (
        <span className="absolute right-4 bottom-4 rounded-pill bg-raised/90 px-3 py-1 text-caption text-ink-muted">
          {extra} more {extra === 1 ? "planting" : "plantings"} in the fields below
        </span>
      )}
    </div>
  );
}

/** WebGL2 is what the 3D view needs; without it the farm screen keeps the still picture. */
export function canDraw3D(): boolean {
  try {
    return Boolean(document.createElement("canvas").getContext("webgl2"));
  } catch {
    return false;
  }
}
