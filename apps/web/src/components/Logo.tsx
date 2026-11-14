import { useId } from "react";

/** The FarmTwin mark (a farm plot on a green tile, one quarter in maize) and the wordmark. The mark
 * keeps its own colours in light and dark mode, like an app icon. */
export default function Logo({ withWordmark = true }: { withWordmark?: boolean }) {
  const clip = useId();
  return (
    <span className="inline-flex items-center gap-2 text-body text-ink">
      <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden>
        <rect width="32" height="32" rx="8" style={{ fill: "var(--mark-tile)" }} />
        <g transform="translate(16 16) scale(1.16) translate(-16 -16)">
          <path d="M5 13.5 16 19v5L5 18.5Z" style={{ fill: "var(--mark-side)" }} />
          <path d="M16 19 27 13.5v5L16 24Z" style={{ fill: "var(--mark-shade)" }} />
          <clipPath id={clip}>
            <path d="M16 8 27 13.5 16 19 5 13.5Z" />
          </clipPath>
          <g clipPath={`url(#${clip})`}>
            <path d="M16 8 27 13.5 16 19 5 13.5Z" style={{ fill: "var(--mark-field)" }} />
            <path d="M21.5 10.75 27 13.5l-5.5 2.75L16 13.5Z" style={{ fill: "var(--mark-maize)" }} />
            <path d="M10.5 10.75 21.5 16.25M21.5 10.75 10.5 16.25" style={{ stroke: "var(--mark-tile)" }} strokeWidth="1.5" />
          </g>
        </g>
      </svg>
      {withWordmark && <span className="font-bold tracking-tight">farmtwin</span>}
    </span>
  );
}
