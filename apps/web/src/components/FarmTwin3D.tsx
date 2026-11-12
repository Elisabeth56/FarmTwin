import { useEffect, useRef, useState } from "react";
import type { Twin } from "@farmtwin/twin";
import type { FieldState, PlantingProgress, Risk } from "../lib/api";
import { cropColor, cropLabel } from "../lib/crops";
import { stageLabel } from "../lib/format";

/** How many plantings the 3D farm has room for; the rest are listed in the field cards. */
const SLOTS = 6;

const SEVERITY_COLOR = {
  high: "var(--risk-high)",
  medium: "var(--risk-medium)",
  low: "var(--risk-low)",
} as const;

type Props = {
  fields: FieldState[];
  risks: Risk[];
  wet: boolean;
  onLog: (fieldId: number) => void;
  onAsk: (question: string) => void;
};

type Drawn = {
  id: number;
  crop: string;
  label: string;
  fieldId: number;
  fieldName: string;
  planting: PlantingProgress;
};

/** This farm's own plantings as a 3D farm: drag or use the buttons to turn it, click a plot for its
 * stage and risks. Three.js loads only when this mounts. */
export default function FarmTwin3D({
  fields,
  risks,
  wet,
  onLog,
  onAsk,
}: Props) {
  const frame = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const badge = useRef<HTMLDivElement>(null);
  const chip = useRef<HTMLDivElement>(null);
  const chipDot = useRef<HTMLSpanElement>(null);
  const chipText = useRef<HTMLSpanElement>(null);
  const twin = useRef<Twin | null>(null);
  const [ready, setReady] = useState(false);
  const [picked, setPicked] = useState<number | null>(null);

  const drawn: Drawn[] = fields
    .flatMap((f) =>
      f.plantings.map((p) => ({
        id: p.id,
        crop: p.crop,
        label: `${cropLabel(p.crop)} · ${f.name}`,
        fieldId: f.id,
        fieldName: f.name,
        planting: p,
      })),
    )
    .slice(0, SLOTS);
  // the badge points at the most urgent risk that has a plot on screen
  const risk = risks.find((r) => drawn.some((d) => d.id === r.planting_id));
  const badgePlot = risk
    ? drawn.findIndex((d) => d.id === risk.planting_id)
    : 0;
  const key = drawn.map((d) => `${d.id}:${d.crop}`).join(",") + `|${badgePlot}`;

  // the scene is rebuilt only when the plots or the badge's plot change
  useEffect(() => {
    let cancelled = false;
    setReady(false);
    setPicked(null);
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
        onSelect: setPicked,
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

  const extra =
    fields.reduce((n, f) => n + f.plantings.length, 0) - drawn.length;
  const plot = picked === null ? null : drawn[picked];
  const plotRisks = plot ? risks.filter((r) => r.planting_id === plot.id) : [];
  const close = () => {
    twin.current?.select(null);
    setPicked(null);
  };

  return (
    // on phones the plot card sits under the farm; from sm up it floats over the corner
    <div className="relative">
      <div
        ref={frame}
        className="relative aspect-[4/3] w-full select-none sm:aspect-[16/7]"
      >
        <canvas
          ref={canvas}
          tabIndex={0}
          aria-label={`3D view of this farm: ${drawn.map((d) => d.label).join(", ")}. Arrow keys turn it, plus and minus zoom, 0 resets.`}
          className={`absolute inset-0 h-full w-full cursor-grab rounded-xl transition-opacity duration-700 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand active:cursor-grabbing ${ready ? "opacity-100" : "opacity-0"}`}
        />
        {!ready && (
          <div
            aria-busy="true"
            aria-label="Loading 3D view"
            className="absolute inset-0 animate-pulse bg-ink/5"
          />
        )}

        <div
          ref={badge}
          className={`pointer-events-none absolute top-0 left-0 z-10 flex flex-col items-center transition-opacity ${ready && risk ? "opacity-100" : "opacity-0"}`}
        >
          {risk && (
            <span className="inline-flex items-center gap-2 rounded-pill bg-ink px-3.5 py-2 text-small whitespace-nowrap text-on-ink">
              <span
                className="size-2 rounded-pill"
                style={{ background: SEVERITY_COLOR[risk.severity] }}
              />
              {risk.title} · {risk.severity}
            </span>
          )}
          <span className="h-11 border-l-2 border-dashed border-ink" />
        </div>

        <div
          ref={chip}
          className="pointer-events-none absolute top-0 left-0 z-10 hidden items-center gap-1.5 rounded-pill bg-raised px-3 py-1.5 text-small whitespace-nowrap shadow-float"
        >
          <span ref={chipDot} className="size-2 rounded-pill" />
          <span ref={chipText} />
        </div>

        {ready && (
          <div className="absolute bottom-3 left-1/2 z-20 flex -translate-x-1/2 items-center gap-1 rounded-pill bg-raised/90 p-1 shadow-float">
            <ViewButton
              label="Turn left"
              onClick={() => twin.current?.turn(-0.4)}
              d="M10 4 5 9l5 5"
            />
            <ViewButton
              label="Turn right"
              onClick={() => twin.current?.turn(0.4)}
              d="M8 4l5 5-5 5"
            />
            <span aria-hidden className="mx-0.5 h-5 w-px bg-hairline" />
            <ViewButton
              label="Zoom in"
              onClick={() => twin.current?.zoom(0.85)}
              d="M9 4v10M4 9h10"
            />
            <ViewButton
              label="Zoom out"
              onClick={() => twin.current?.zoom(1.18)}
              d="M4 9h10"
            />
            <span aria-hidden className="mx-0.5 h-5 w-px bg-hairline" />
            <ViewButton
              label="Reset view"
              onClick={() => twin.current?.resetView()}
              d="M4.5 9a4.5 4.5 0 1 0 1.4-3.3M4.5 3.5v2.4h2.4"
            />
          </div>
        )}

        {ready && !plot && (
          <span className="pointer-events-none absolute bottom-4 left-4 hidden rounded-pill bg-raised/90 px-3 py-1 text-caption text-ink-muted sm:block">
            Click a plot for details
            {extra > 0 ? ` · ${extra} more in the fields below` : ""}
          </span>
        )}
      </div>

      {plot && (
        <div
          role="dialog"
          aria-label={plot.label}
          className="z-20 m-3 mt-0 flex animate-rise flex-col gap-3 rounded-lg bg-surface p-4 sm:absolute sm:bottom-4 sm:left-4 sm:m-0 sm:w-80 sm:bg-raised sm:shadow-float"
        >
          <div className="flex items-start justify-between gap-2">
            <span className="inline-flex items-center gap-2 text-body">
              <span
                aria-hidden
                className="size-2.5 rounded-pill"
                style={{ background: cropColor(plot.crop) }}
              />
              {cropLabel(plot.crop)} · {plot.fieldName}
            </span>
            <button
              type="button"
              onClick={close}
              aria-label="Close"
              className="-m-2 grid size-9 place-items-center rounded-pill text-ink-muted hover:bg-ink/5"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
                <path
                  d="M3 3l8 8M11 3l-8 8"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>
          <span className="text-small text-ink-muted">
            {sentence(stageLabel(plot.planting.stage))}
            {plot.planting.day !== null &&
              ` · day ${plot.planting.day} of about ${plot.planting.cycle_days}`}
          </span>
          {plotRisks.length > 0 ? (
            <ul className="flex flex-col gap-1.5">
              {plotRisks.map((r) => (
                <li
                  key={r.id}
                  className="inline-flex items-center gap-2 text-small"
                >
                  <span
                    aria-hidden
                    className="size-2 shrink-0 rounded-pill"
                    style={{ background: SEVERITY_COLOR[r.severity] }}
                  />
                  {r.title}
                </li>
              ))}
            </ul>
          ) : (
            <span className="text-small text-ink-muted">No open risks.</span>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => onLog(plot.fieldId)}
              className="min-h-10 flex-1 rounded-pill bg-ink px-3 text-small text-on-ink hover:opacity-90"
            >
              Log for {plot.fieldName}
            </button>
            <button
              type="button"
              onClick={() =>
                onAsk(
                  `What should I do for my ${cropLabel(plot.crop).toLowerCase()} in ${plot.fieldName} this week?`,
                )
              }
              className="min-h-10 flex-1 rounded-pill bg-ink/5 px-3 text-small text-ink hover:bg-ink/10"
            >
              Ask about it
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

const sentence = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function ViewButton({
  label,
  d,
  onClick,
}: {
  label: string;
  d: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="grid size-9 place-items-center rounded-pill text-ink hover:bg-ink/5 focus-visible:outline-2 focus-visible:outline-brand"
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 18 18"
        aria-hidden
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d={d} />
      </svg>
    </button>
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
