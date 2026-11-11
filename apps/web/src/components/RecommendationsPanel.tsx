import { useMemo, useState } from "react";
import Card from "./Card";
import RecommendationCard from "./RecommendationCard";
import type { Recommendation } from "../lib/api";

type Props = {
  recommendations: Recommendation[];
};

const PRIORITY_RANK: Record<Recommendation["priority"], number> = {
  high: 0,
  medium: 1,
  low: 2,
};

const DEFAULT_VISIBLE = 5;

export default function RecommendationsPanel({ recommendations }: Props) {
  const [showAll, setShowAll] = useState(false);

  const sorted = useMemo(() => {
    return [...recommendations].sort(
      (a, b) => PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority],
    );
  }, [recommendations]);

  const visible = showAll ? sorted : sorted.slice(0, DEFAULT_VISIBLE);
  const hiddenCount = sorted.length - visible.length;

  return (
    <Card>
      <div className="text-caption uppercase tracking-wide text-ink-faint">
        Recommendations
      </div>
      {sorted.length === 0 ? (
        <div className="mt-3 text-small text-ink-muted">
          Ask FarmTwin a question to see recommendations.
        </div>
      ) : (
        <div className="mt-4 flex flex-col gap-3">
          {visible.map((rec, i) => (
            <RecommendationCard key={i} recommendation={rec} />
          ))}
          {hiddenCount > 0 && (
            <button
              type="button"
              onClick={() => setShowAll(true)}
              className="text-small text-brand hover:underline self-start"
            >
              Show older ({hiddenCount})
            </button>
          )}
        </div>
      )}
    </Card>
  );
}
