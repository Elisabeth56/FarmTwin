type Level = "high" | "medium" | "low";

const DOT: Record<Level, string> = {
  high: "bg-risk-high",
  medium: "bg-risk-medium",
  low: "bg-risk-low",
};

type RiskBadgeProps = {
  name: string;
  level: Level;
  onClick?: () => void;
  /** name only, for when the name already is the level ("High") */
  compact?: boolean;
};

/** An ink pill naming a rule-based risk. The level is always written out, never colour alone. */
export default function RiskBadge({ name, level, onClick, compact = false }: RiskBadgeProps) {
  const content = (
    <>
      <span aria-hidden className={`size-2 rounded-pill ${DOT[level]}`} />
      <span>{name}</span>
      {!compact && <span className="opacity-70">· {level}</span>}
    </>
  );
  const className = "inline-flex shrink-0 items-center gap-2 rounded-pill bg-ink px-3 py-1 text-small whitespace-nowrap text-on-ink";
  if (!onClick) return <span className={className}>{content}</span>;
  return (
    <button type="button" onClick={onClick} className={`${className} min-h-11`}>
      {content}
    </button>
  );
}
