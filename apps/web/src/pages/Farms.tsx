import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import Button from "../components/Button";
import CropChip from "../components/CropChip";
import FieldMosaic from "../components/FieldMosaic";
import RiskBadge from "../components/RiskBadge";
import { createSampleFarm, getFarmSummaries, type FarmSummary, type Risk } from "../lib/api";
import { CROPS, cropLabel } from "../lib/crops";
import { useModel } from "../lib/model";
import { recall, remember } from "../lib/storage";
import { SETUP_SEEN } from "./ModelSetup";
import { loggedAgo } from "../lib/time";

const FILTER_KEY = "ft.farms.crop";
const SEVERITY = { high: 0, medium: 1, low: 2 } as const;

type Load = { state: "loading" } | { state: "error"; message: string } | { state: "ready"; farms: FarmSummary[] };

export default function Farms() {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const { status } = useModel();

  useEffect(() => {
    getFarmSummaries()
      .then((farms) => setLoad({ state: "ready", farms }))
      .catch((e: Error) => setLoad({ state: "error", message: e.message }));
  }, []);

  // the very first launch goes to model setup; after that it's one click away in the sidebar
  if (status?.state === "not_set_up" && !recall(SETUP_SEEN)) return <Navigate to="/setup/model" replace />;
  if (load.state === "ready" && load.farms.length === 0) return <EmptyFarms />;
  return (
    <AppShell>
      {load.state === "loading" && <FarmsSkeleton />}
      {load.state === "error" && <p className="text-body text-risk-high">{load.message}</p>}
      {load.state === "ready" && <FarmList farms={load.farms} />}
    </AppShell>
  );
}

function FarmList({ farms }: { farms: FarmSummary[] }) {
  const [crop, setCrop] = useState<string>(() => recall(FILTER_KEY) ?? "all");
  const [query, setQuery] = useState("");

  const pick = (value: string) => {
    setCrop(value);
    remember(FILTER_KEY, value);
  };

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return farms.filter(
      (f) =>
        (crop === "all" || f.plots.some((p) => p.crop === crop)) &&
        (!q || f.name.toLowerCase().includes(q) || (f.region ?? "").toLowerCase().includes(q)),
    );
  }, [farms, crop, query]);

  // each farm's most severe risk (the API sorts them), most severe farms first
  const attention = shown
    .filter((farm) => farm.risks[0] && farm.risks[0].severity !== "low")
    .map((farm) => ({ farm, risk: farm.risks[0] }))
    .sort((a, b) => SEVERITY[a.risk.severity] - SEVERITY[b.risk.severity])
    .slice(0, 4);
  const needing = attention.length;

  return (
    <div className="flex flex-col gap-8">
      <header className="flex animate-rise flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-h2">Your farms</h1>
          <p className="text-body text-ink-muted">{summaryLine(shown.length, crop, needing)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex min-h-11 items-center gap-2 rounded-pill bg-raised px-4 ring-1 ring-hairline ring-inset">
            <span className="sr-only">Search farms</span>
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden className="text-ink-muted">
              <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.6" fill="none" />
              <path d="M11 11l3 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search farms or towns"
              className="w-44 bg-transparent text-small text-ink outline-none placeholder:text-ink-muted"
            />
          </label>
          <Link to="/setup" className="inline-flex min-h-11 items-center rounded-pill bg-ink px-5 text-small text-on-ink transition duration-150 ease-ui hover:bg-ink/90">
            New farm
          </Link>
        </div>
      </header>

      <div role="group" aria-label="Filter by crop" className="flex animate-rise flex-wrap gap-2 [animation-delay:80ms]">
        <button
          type="button"
          aria-pressed={crop === "all"}
          onClick={() => pick("all")}
          className={`inline-flex min-h-11 items-center gap-1 rounded-pill px-3 text-small text-ink ${crop === "all" ? "bg-brand-tint" : "bg-surface ring-1 ring-hairline ring-inset"}`}
        >
          All crops
        </button>
        {CROPS.map((c) => (
          <CropChip key={c} crop={c} selected={crop === c} onClick={() => pick(c)} />
        ))}
      </div>

      {attention.length > 0 && (
        <section className="flex animate-rise flex-col gap-3 [animation-delay:160ms]">
          <h2 className="text-small text-ink-muted">Needs attention this week</h2>
          <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(300px,1fr))]">
            {attention.map(({ farm, risk }) => (
              <AttentionCard key={farm.id} farm={farm} risk={risk} />
            ))}
          </div>
        </section>
      )}

      {shown.length === 0 ? (
        <p className="text-body text-ink-muted">No farms match. Try another crop or clear the search.</p>
      ) : (
        <section className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]">
          {shown.map((farm, i) => (
            <FarmCard key={farm.id} farm={farm} delay={200 + i * 60} />
          ))}
        </section>
      )}
    </div>
  );
}

function AttentionCard({ farm, risk }: { farm: FarmSummary; risk: Risk }) {
  return (
    <Link
      to={`/farm/${farm.id}`}
      className="flex items-center gap-4 rounded-lg bg-raised px-5 py-4 transition duration-300 ease-reveal hover:-translate-y-1 hover:shadow-float"
    >
      <RiskBadge name={risk.severity === "high" ? "High" : "Medium"} level={risk.severity} compact />
      <span className="flex flex-col">
        <span className="text-body">
          {risk.title} · {cropLabel(risk.crop).toLowerCase()}
        </span>
        <span className="text-small text-ink-muted">
          {farm.name} · {risk.field}
        </span>
      </span>
    </Link>
  );
}

function FarmCard({ farm, delay }: { farm: FarmSummary; delay: number }) {
  const top = farm.risks[0];
  const crops = [...new Set(farm.plots.map((p) => p.crop))];
  return (
    <Link
      to={`/farm/${farm.id}`}
      style={{ animationDelay: `${delay}ms` }}
      className="flex animate-rise flex-col gap-4 rounded-lg bg-raised p-5 transition duration-300 ease-reveal hover:-translate-y-1 hover:shadow-float"
    >
      <FieldMosaic plots={farm.plots} />
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col">
          <span className="text-h3">{farm.name}</span>
          <span className="text-small text-ink-muted">
            {[farm.region, farm.area_hectares && `${farm.area_hectares} ha`].filter(Boolean).join(" · ") || "No location yet"}
          </span>
        </div>
        {top && top.severity !== "low" && (
          <RiskBadge name={top.severity === "high" ? "High" : "Medium"} level={top.severity} compact />
        )}
      </div>
      {crops.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {crops.map((c) => (
            <CropChip key={c} crop={c} />
          ))}
        </div>
      ) : (
        <span className="text-small text-ink-muted">Nothing planted yet</span>
      )}
      <span className="text-caption text-ink-muted">{loggedAgo(farm.last_logged_at)}</span>
    </Link>
  );
}

function FarmsSkeleton() {
  return (
    <div className="flex flex-col gap-8" aria-busy="true" aria-label="Loading farms">
      <div className="h-11 w-56 rounded-md bg-ink/5" />
      <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-64 rounded-lg bg-ink/5" />
        ))}
      </div>
    </div>
  );
}

function summaryLine(count: number, crop: string, needing: number): string {
  const farms = `${count} ${count === 1 ? "farm" : "farms"}`;
  if (crop !== "all") return `${farms} growing ${crop}`;
  if (needing === 0) return `${farms} · nothing urgent this week`;
  return `${farms} · ${needing} ${needing === 1 ? "needs" : "need"} attention this week`;
}

function EmptyFarms() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const explore = async () => {
    setBusy(true);
    setError(null);
    try {
      const farm = await createSampleFarm();
      navigate(`/farm/${farm.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  return (
    <AppShell>
      <section className="flex min-h-[calc(100dvh-8rem)] flex-col justify-between overflow-hidden rounded-xl bg-raised md:min-h-[calc(100dvh-5rem)]">
        <div className="flex max-w-xl animate-rise flex-col gap-5 px-6 pt-12 md:px-12 md:pt-14">
          <h1 className="text-h2 md:text-h1">Add the first farm you look after.</h1>
          <p className="text-lead text-ink-muted">
            A name, the nearest town and what's planted. You can add fields and logs after.
          </p>
          <div className="flex flex-wrap gap-2">
            <Link to="/setup" className="inline-flex min-h-11 items-center rounded-pill bg-ink px-5 text-small text-on-ink transition duration-150 ease-ui hover:bg-ink/90">
              Add a farm
            </Link>
            <Button variant="secondary" onClick={explore} disabled={busy}>
              {busy ? "Setting up the sample…" : "Explore a sample farm"}
            </Button>
          </div>
          {error && <p className="text-small text-risk-high">{error}</p>}
          <div className="flex flex-wrap gap-2">
            {CROPS.map((c) => (
              <CropChip key={c} crop={c} />
            ))}
          </div>
        </div>
        <Wordmark />
      </section>
    </AppShell>
  );
}

/** The oversized wordmark; each letter takes the brand colour on hover. */
function Wordmark() {
  return (
    <div aria-hidden className="flex px-6 pt-10 text-[23vw] leading-[0.82] tracking-[-0.06em] select-none md:px-8 md:text-[15vw] xl:text-[min(15vw,220px)]" style={{ marginBottom: "-0.14em" }}>
      {"farmtwin".split("").map((ch, i) => (
        <span key={i} className="transition-colors duration-300 ease-ui hover:text-brand">
          {ch}
        </span>
      ))}
    </div>
  );
}
