import { useMemo } from "react";
import Card from "./Card";
import type { Observation } from "../lib/api";

type Props = {
  observations: Observation[];
};

type DerivedRisk = {
  level: "high" | "medium";
  title: string;
  detail?: string;
};

const LEVEL_STYLES: Record<DerivedRisk["level"], string> = {
  high: "border-l-risk-high bg-risk-high/5",
  medium: "border-l-risk-medium bg-risk-medium/5",
};

const LEVEL_LABEL: Record<DerivedRisk["level"], string> = {
  high: "text-risk-high",
  medium: "text-risk-medium",
};

function daysAgo(iso: string): number {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return Number.POSITIVE_INFINITY;
  const diff = Date.now() - then;
  return diff / (1000 * 60 * 60 * 24);
}

function deriveRisks(observations: Observation[]): DerivedRisk[] {
  const risks: DerivedRisk[] = [];

  const heavyRain = observations.find(
    (o) =>
      o.obs_type === "rainfall" &&
      o.value_numeric !== null &&
      o.value_numeric !== undefined &&
      o.value_numeric >= 50 &&
      daysAgo(o.observed_at) <= 5,
  );
  if (heavyRain) {
    risks.push({
      level: "high",
      title: "Heavy recent rainfall",
      detail: `${heavyRain.value_numeric} mm logged — inspect for fungal disease.`,
    });
  }

  const highHumidity = observations.find(
    (o) =>
      o.obs_type === "humidity" &&
      o.value_numeric !== null &&
      o.value_numeric !== undefined &&
      o.value_numeric >= 80,
  );
  if (highHumidity) {
    risks.push({
      level: "medium",
      title: "Sustained high humidity",
      detail: `${highHumidity.value_numeric}% — foliar disease pressure.`,
    });
  }

  const pest = observations.find(
    (o) => o.obs_type === "pest" && daysAgo(o.observed_at) <= 7,
  );
  if (pest) {
    risks.push({
      level: "high",
      title: "Pest reported",
      detail: pest.value_text ?? undefined,
    });
  }

  const disease = observations.find(
    (o) => o.obs_type === "disease" && daysAgo(o.observed_at) <= 7,
  );
  if (disease) {
    risks.push({
      level: "high",
      title: "Disease reported",
      detail: disease.value_text ?? undefined,
    });
  }

  return risks;
}

export default function RisksPanel({ observations }: Props) {
  const risks = useMemo(() => deriveRisks(observations), [observations]);

  return (
    <Card>
      <div className="text-caption uppercase tracking-wide text-ink-faint">
        Risks
      </div>
      {risks.length === 0 ? (
        <div className="mt-3 text-small text-ink-muted">
          No active risks based on observations. Log recent farm conditions to
          see risks.
        </div>
      ) : (
        <div className="mt-4 flex flex-col gap-2">
          {risks.map((r, i) => (
            <div
              key={i}
              className={`rounded-md border border-hairline border-l-4 ${LEVEL_STYLES[r.level]} px-3 py-2`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`text-[10px] uppercase tracking-wide font-semibold ${LEVEL_LABEL[r.level]}`}
                >
                  {r.level}
                </span>
                <span className="text-small font-medium text-ink">
                  {r.title}
                </span>
              </div>
              {r.detail && (
                <div className="text-caption text-ink-muted mt-1">{r.detail}</div>
              )}
            </div>
          ))}
        </div>
      )}
      <div className="text-[11px] text-ink-faint mt-3">
        Ask FarmTwin for a full risk assessment.
      </div>
    </Card>
  );
}
