import type { Recommendation } from "../lib/api";

type Props = {
  recommendation: Recommendation;
};

const PRIORITY_BORDER: Record<Recommendation["priority"], string> = {
  high: "border-l-risk-high",
  medium: "border-l-risk-medium",
  low: "border-l-risk-low",
};

const PRIORITY_PILL: Record<Recommendation["priority"], string> = {
  high: "bg-risk-high/10 text-risk-high",
  medium: "bg-risk-medium/10 text-risk-medium",
  low: "bg-risk-low/10 text-risk-low",
};

export default function RecommendationCard({ recommendation }: Props) {
  const p = recommendation.priority;
  return (
    <div
      className={`rounded-md border border-hairline border-l-4 ${PRIORITY_BORDER[p]} bg-raised p-4`}
    >
      <div className="flex items-center gap-2 flex-wrap">
        <span
          className={`text-[10px] uppercase tracking-wide font-semibold px-2 py-0.5 rounded-pill ${PRIORITY_PILL[p]}`}
        >
          {p}
        </span>
        {recommendation.when_urgency && (
          <span className="text-[10px] uppercase tracking-wide text-ink-muted bg-brand-tint px-2 py-0.5 rounded-pill">
            {recommendation.when_urgency}
          </span>
        )}
      </div>
      <div className="text-body font-semibold text-ink mt-2">
        {recommendation.what}
      </div>
      {recommendation.why && (
        <div className="text-small text-ink-muted mt-2">{recommendation.why}</div>
      )}
      {recommendation.risk_if_ignored && (
        <div className="text-caption text-ink-faint mt-3">
          <span className="font-semibold uppercase tracking-wide mr-1">
            Risk if ignored:
          </span>
          {recommendation.risk_if_ignored}
        </div>
      )}
    </div>
  );
}
