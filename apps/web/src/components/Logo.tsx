/** The FarmTwin mark (a farm plot as an isometric slab) and wordmark, drawn from the tokens. */
export default function Logo({ withWordmark = true }: { withWordmark?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2 text-body text-ink">
      <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden>
        <path d="M3 9.5 16 16v6.5L3 16Z" fill="var(--ink)" stroke="var(--ink)" strokeLinejoin="round" />
        <path d="M16 16 29 9.5V16L16 22.5Z" fill="var(--ink)" stroke="var(--ink)" strokeLinejoin="round" />
        <path d="M16 16 29 9.5V16L16 22.5Z" fill="black" opacity="0.25" />
        <g stroke="var(--ground)" strokeWidth="1.4" strokeLinejoin="round">
          <path d="M16 3l6.5 3.25L16 9.5 9.5 6.25Z" fill="var(--brand)" />
          <path d="M22.5 6.25 29 9.5l-6.5 3.25L16 9.5Z" fill="var(--crop-maize)" />
          <path d="M16 9.5l6.5 3.25L16 16l-6.5-3.25Z" fill="var(--brand)" />
          <path d="M9.5 6.25 16 9.5l-6.5 3.25L3 9.5Z" fill="var(--brand)" opacity="0.8" />
        </g>
      </svg>
      {withWordmark && <span className="tracking-tight">FarmTwin</span>}
    </span>
  );
}
