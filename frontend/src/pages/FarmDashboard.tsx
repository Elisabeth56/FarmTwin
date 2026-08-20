import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import AskPanel from "../components/AskPanel";
import Button from "../components/Button";
import Card from "../components/Card";
import LogObservationModal from "../components/LogObservationModal";
import LogWeatherModal from "../components/LogWeatherModal";
import RecommendationsPanel from "../components/RecommendationsPanel";
import RisksPanel from "../components/RisksPanel";
import SourceDrawer from "../components/SourceDrawer";
import {
  getCrops,
  getFarm,
  getFields,
  getObservations,
  getWeather,
  type CitedChunk,
  type Crop,
  type Farm,
  type Field,
  type Observation,
  type Recommendation,
  type WeatherSnapshot,
} from "../lib/api";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | {
      kind: "ready";
      farm: Farm;
      fields: Field[];
      crops: Crop[];
      observations: Observation[];
      weather: WeatherSnapshot[];
    };

const STAGES = [
  "germination",
  "seedling",
  "vegetative",
  "flowering",
  "grain_filling",
  "maturity",
] as const;
type Stage = (typeof STAGES)[number];

const STAGE_LABELS: Record<Stage, string> = {
  germination: "Germination",
  seedling: "Seedling",
  vegetative: "Vegetative",
  flowering: "Flowering",
  grain_filling: "Grain fill",
  maturity: "Maturity",
};

function estimateStage(cropType: string, daysSincePlanting: number): Stage {
  const t = cropType.toLowerCase();
  if (t === "maize") {
    if (daysSincePlanting < 7) return "germination";
    if (daysSincePlanting < 21) return "seedling";
    if (daysSincePlanting < 60) return "vegetative";
    if (daysSincePlanting < 75) return "flowering";
    if (daysSincePlanting < 105) return "grain_filling";
    return "maturity";
  }
  if (t === "rice") {
    if (daysSincePlanting < 10) return "germination";
    if (daysSincePlanting < 30) return "seedling";
    if (daysSincePlanting < 65) return "vegetative";
    if (daysSincePlanting < 85) return "flowering";
    if (daysSincePlanting < 110) return "grain_filling";
    return "maturity";
  }
  if (daysSincePlanting < 14) return "germination";
  if (daysSincePlanting < 45) return "seedling";
  if (daysSincePlanting < 120) return "vegetative";
  if (daysSincePlanting < 180) return "flowering";
  if (daysSincePlanting < 240) return "grain_filling";
  return "maturity";
}

function daysBetween(fromISO: string, to: Date = new Date()): number {
  const from = new Date(fromISO);
  const ms = to.getTime() - from.getTime();
  return Math.max(0, Math.floor(ms / (1000 * 60 * 60 * 24)));
}

function shortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function obsPillClasses(obsType: string): string {
  switch (obsType) {
    case "rainfall":
      return "bg-blue-50 text-blue-700";
    case "humidity":
      return "bg-cyan-50 text-cyan-700";
    case "pest":
    case "disease":
      return "bg-risk-high/10 text-risk-high";
    case "temperature":
      return "bg-amber-50 text-amber-700";
    default:
      return "bg-primary-tint text-primary";
  }
}

function obsValue(o: Observation): string {
  if (o.value_numeric !== null && o.value_numeric !== undefined) {
    return `${o.value_numeric}${o.unit ? ` ${o.unit}` : ""}`;
  }
  return o.value_text ?? "—";
}

export default function FarmDashboard() {
  const { id } = useParams<{ id: string }>();
  const farmId = Number(id);
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [activeChunk, setActiveChunk] = useState<CitedChunk | null>(null);
  const [logObservationOpen, setLogObservationOpen] = useState(false);
  const [logWeatherOpen, setLogWeatherOpen] = useState(false);

  const loadAll = useCallback(() => {
    if (!Number.isFinite(farmId)) {
      setState({ kind: "error", message: "Invalid farm id" });
      return Promise.resolve();
    }
    return Promise.all([
      getFarm(farmId),
      getFields(farmId),
      getCrops(farmId),
      getObservations(farmId),
      getWeather(farmId),
    ])
      .then(([farm, fields, crops, observations, weather]) => {
        setState({
          kind: "ready",
          farm,
          fields,
          crops,
          observations,
          weather,
        });
      })
      .catch((err) => {
        setState({
          kind: "error",
          message: err instanceof Error ? err.message : "Failed to load farm.",
        });
      });
  }, [farmId]);

  useEffect(() => {
    let cancelled = false;
    if (!Number.isFinite(farmId)) {
      setState({ kind: "error", message: "Invalid farm id" });
      return;
    }
    Promise.all([
      getFarm(farmId),
      getFields(farmId),
      getCrops(farmId),
      getObservations(farmId),
      getWeather(farmId),
    ])
      .then(([farm, fields, crops, observations, weather]) => {
        if (cancelled) return;
        setState({
          kind: "ready",
          farm,
          fields,
          crops,
          observations,
          weather,
        });
      })
      .catch((err) => {
        if (cancelled) return;
        setState({
          kind: "error",
          message: err instanceof Error ? err.message : "Failed to load farm.",
        });
      });
    return () => {
      cancelled = true;
    };
  }, [farmId]);

  const activeCrop = useMemo<Crop | undefined>(() => {
    if (state.kind !== "ready") return undefined;
    const active = state.crops.find((c) => c.status === "active");
    return active ?? state.crops[0];
  }, [state]);

  const latestWeather = useMemo<WeatherSnapshot | undefined>(() => {
    if (state.kind !== "ready") return undefined;
    return [...state.weather].sort((a, b) =>
      a.snapshot_date < b.snapshot_date ? 1 : -1,
    )[0];
  }, [state]);

  const recentObservations = useMemo<Observation[]>(() => {
    if (state.kind !== "ready") return [];
    return [...state.observations]
      .sort((a, b) => (a.observed_at < b.observed_at ? 1 : -1))
      .slice(0, 10);
  }, [state]);

  const allObservations = useMemo<Observation[]>(() => {
    if (state.kind !== "ready") return [];
    return state.observations;
  }, [state]);

  const primaryFieldId = useMemo<number | undefined>(() => {
    if (state.kind !== "ready") return undefined;
    if (activeCrop) return activeCrop.field_id;
    return state.fields[0]?.id;
  }, [state, activeCrop]);

  const handleNewRecommendations = useCallback((recs: Recommendation[]) => {
    setRecommendations((prev) => [...recs, ...prev]);
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <Header
        farmName={state.kind === "ready" ? state.farm.name : undefined}
        region={
          state.kind === "ready" ? (state.farm.region ?? undefined) : undefined
        }
      />

      <main className="flex-1 w-full max-w-[1400px] mx-auto px-6 py-8">
        {state.kind === "loading" && (
          <div className="text-ink-muted">Loading farm…</div>
        )}

        {state.kind === "error" && (
          <Card>
            <div className="text-risk-high font-medium">
              Couldn't load this farm
            </div>
            <div className="text-sm text-ink-muted mt-2">{state.message}</div>
            <div className="mt-4">
              <Link to="/" className="text-primary hover:underline text-sm">
                ← Back to landing
              </Link>
            </div>
          </Card>
        )}

        {state.kind === "ready" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 flex flex-col gap-4">
              <CropCard crop={activeCrop} />
              <WeatherCard
                snapshot={latestWeather}
                onLog={() => setLogWeatherOpen(true)}
              />
              <ObservationsCard
                observations={recentObservations}
                canLog={primaryFieldId !== undefined}
                onLog={() => setLogObservationOpen(true)}
              />
            </div>
            <div className="flex flex-col gap-4">
              <RisksPanel observations={allObservations} />
              <RecommendationsPanel recommendations={recommendations} />
              <AskPanel
                farmId={farmId}
                onCitationClick={setActiveChunk}
                onNewRecommendations={handleNewRecommendations}
              />
            </div>
          </div>
        )}
      </main>

      {primaryFieldId !== undefined && (
        <LogObservationModal
          isOpen={logObservationOpen}
          fieldId={primaryFieldId}
          onClose={() => setLogObservationOpen(false)}
          onSuccess={() => {
            void loadAll();
          }}
        />
      )}
      <LogWeatherModal
        isOpen={logWeatherOpen}
        farmId={farmId}
        onClose={() => setLogWeatherOpen(false)}
        onSuccess={() => {
          void loadAll();
        }}
      />
      <SourceDrawer
        chunk={activeChunk}
        onClose={() => setActiveChunk(null)}
      />
    </div>
  );
}

function Header({
  farmName,
  region,
}: {
  farmName?: string;
  region?: string;
}) {
  return (
    <header className="h-16 border-b border-border bg-card">
      <div className="h-full max-w-[1400px] mx-auto px-6 flex items-center justify-between">
        <Link to="/" className="text-lg font-semibold text-primary">
          🌱 FarmTwin
        </Link>
        {farmName && (
          <div className="flex items-center gap-3">
            <span className="font-medium text-ink">{farmName}</span>
            {region && (
              <span className="rounded-full bg-primary-tint text-primary px-3 py-1 text-sm">
                {region}
              </span>
            )}
          </div>
        )}
      </div>
    </header>
  );
}

function CropCard({ crop }: { crop?: Crop }) {
  if (!crop) {
    return (
      <Card>
        <div className="text-xs uppercase tracking-wide text-ink-faint">
          Current crop
        </div>
        <div className="mt-3 text-ink-muted">No crops recorded yet.</div>
      </Card>
    );
  }

  const days = crop.planting_date ? daysBetween(crop.planting_date) : 0;
  const stage = estimateStage(crop.crop_type, days);

  return (
    <Card>
      <div className="text-xs uppercase tracking-wide text-ink-faint">
        Current crop
      </div>
      <div className="mt-3 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="text-3xl font-semibold capitalize">
            {crop.crop_type}
          </div>
          {crop.variety && (
            <div className="text-ink-muted mt-1">{crop.variety}</div>
          )}
          <div className="text-sm text-ink-muted mt-3 tabular">
            {crop.planting_date
              ? `Planted ${shortDate(crop.planting_date)} · ${days} days ago`
              : "No planting date"}
          </div>
        </div>
        <span className="rounded-full bg-primary-tint text-primary px-3 py-1 text-sm">
          {STAGE_LABELS[stage]}
        </span>
      </div>

      <div className="mt-6">
        <div className="text-xs uppercase tracking-wide text-ink-faint mb-3">
          Timeline
        </div>
        <StageStrip currentStage={stage} />
      </div>
    </Card>
  );
}

function StageStrip({ currentStage }: { currentStage: Stage }) {
  const currentIndex = STAGES.indexOf(currentStage);
  return (
    <div className="flex gap-1.5">
      {STAGES.map((stage, i) => {
        const isCurrent = i === currentIndex;
        const isPast = i < currentIndex;
        const bar = isCurrent
          ? "bg-primary"
          : isPast
            ? "bg-primary/40"
            : "bg-border";
        const label = isCurrent
          ? "text-ink font-medium"
          : isPast
            ? "text-ink-muted"
            : "text-ink-faint";
        return (
          <div key={stage} className="flex-1">
            <div className={`h-1.5 rounded-full ${bar}`} />
            <div className={`text-[11px] mt-2 ${label}`}>
              {STAGE_LABELS[stage]}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function WeatherCard({
  snapshot,
  onLog,
}: {
  snapshot?: WeatherSnapshot;
  onLog: () => void;
}) {
  if (!snapshot) {
    return (
      <Card>
        <div className="flex items-center justify-between">
          <div className="text-xs uppercase tracking-wide text-ink-faint">
            Weather
          </div>
        </div>
        <div className="mt-4 text-ink-muted">No weather snapshots yet</div>
        <div className="mt-4">
          <Button variant="secondary" onClick={onLog}>
            Log weather
          </Button>
        </div>
      </Card>
    );
  }

  const hasTempRange =
    snapshot.temp_min_c !== null && snapshot.temp_max_c !== null;

  return (
    <Card>
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-wide text-ink-faint">
          Weather
        </div>
        <div className="flex items-center gap-3">
          <div className="text-xs text-ink-faint tabular">
            {shortDate(snapshot.snapshot_date)}
          </div>
          <button
            type="button"
            onClick={onLog}
            className="text-sm text-primary hover:underline"
            aria-label="Log another weather snapshot"
          >
            + Add
          </button>
        </div>
      </div>
      <div className="mt-3 flex items-baseline gap-6 flex-wrap">
        {hasTempRange && (
          <div>
            <div className="text-3xl font-semibold tabular">
              {snapshot.temp_min_c}–{snapshot.temp_max_c}
              <span className="text-lg text-ink-muted">°C</span>
            </div>
            <div className="text-xs text-ink-faint mt-1">temperature</div>
          </div>
        )}
        {snapshot.humidity_pct !== null && (
          <div>
            <div className="text-2xl font-semibold tabular">
              {snapshot.humidity_pct}
              <span className="text-base text-ink-muted">%</span>
            </div>
            <div className="text-xs text-ink-faint mt-1">humidity</div>
          </div>
        )}
        {snapshot.rainfall_mm !== null && (
          <div>
            <div className="text-2xl font-semibold tabular">
              {snapshot.rainfall_mm}
              <span className="text-base text-ink-muted"> mm</span>
            </div>
            <div className="text-xs text-ink-faint mt-1">rainfall</div>
          </div>
        )}
      </div>
      {snapshot.notes && (
        <div className="text-sm text-ink-muted mt-4">{snapshot.notes}</div>
      )}
    </Card>
  );
}

function ObservationsCard({
  observations,
  canLog,
  onLog,
}: {
  observations: Observation[];
  canLog: boolean;
  onLog: () => void;
}) {
  return (
    <Card>
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-wide text-ink-faint">
          Recent observations
        </div>
        <Button
          variant="secondary"
          onClick={onLog}
          disabled={!canLog}
          className="!px-4 !py-2 text-sm"
        >
          + Log observation
        </Button>
      </div>

      {observations.length === 0 ? (
        <div className="mt-6 text-ink-muted text-sm">
          No observations yet. Log what you see on the farm — rainfall, pests,
          humidity — to give FarmTwin better context.
        </div>
      ) : (
        <ul className="mt-4 divide-y divide-border">
          {observations.map((o) => (
            <li
              key={o.id}
              className="py-3 flex items-center gap-4 flex-wrap"
            >
              <span className="text-sm text-ink-muted tabular w-16 shrink-0">
                {shortDate(o.observed_at)}
              </span>
              <span
                className={`text-xs rounded-full px-2.5 py-1 ${obsPillClasses(o.obs_type)}`}
              >
                {o.obs_type}
              </span>
              <span className="text-sm text-ink tabular">{obsValue(o)}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
