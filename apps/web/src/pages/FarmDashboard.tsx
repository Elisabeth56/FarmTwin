import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import AskPanel, { type AskContextChip } from "../components/AskPanel";
import Button from "../components/Button";
import FieldCard from "../components/FieldCard";
import LogSheet from "../components/LogSheet";
import ModelStoppedCard from "../components/ModelStoppedCard";
import RainChart from "../components/RainChart";
import RiskList from "../components/RiskList";
import SourceDrawer from "../components/SourceDrawer";
import {
  deleteObservation,
  getFarmDashboard,
  type CitedChunk,
  type FarmDashboardData,
  type Observation,
} from "../lib/api";
import { cropLabel } from "../lib/crops";
import { stageLabel } from "../lib/format";

type Load = { state: "loading" } | { state: "error"; message: string } | { state: "ready"; data: FarmDashboardData };
type Undo = { obs: Observation; label: string };

/** Rain at or above this in the last three days switches the twin to its wet look. */
const WET_MM = 20;

export default function FarmDashboard() {
  const farmId = Number(useParams<{ id: string }>().id);
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [logOpen, setLogOpen] = useState(false);
  const [undo, setUndo] = useState<Undo | null>(null);
  const [chunk, setChunk] = useState<CitedChunk | null>(null);

  const refresh = useCallback(
    () =>
      getFarmDashboard(farmId)
        .then((data) => setLoad({ state: "ready", data }))
        .catch((e: Error) => setLoad({ state: "error", message: e.message })),
    [farmId],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // the undo offer stays for 8 seconds after a log
  useEffect(() => {
    if (!undo) return;
    const timer = setTimeout(() => setUndo(null), 8000);
    return () => clearTimeout(timer);
  }, [undo]);

  const undoLast = async () => {
    if (!undo) return;
    setUndo(null);
    await deleteObservation(undo.obs.id);
    await refresh();
  };

  if (load.state !== "ready") {
    return (
      <AppShell>
        {load.state === "loading" ? (
          <div aria-busy="true" aria-label="Loading farm" className="flex flex-col gap-6">
            <div className="h-14 w-72 rounded-md bg-ink/5" />
            <div className="aspect-[16/7] rounded-xl bg-ink/5" />
          </div>
        ) : (
          <p className="text-body text-risk-high">{load.message}</p>
        )}
      </AppShell>
    );
  }

  const { farm, fields, rainfall, risks } = load.data;
  const wet = rainfall.slice(-3).some((d) => (d.mm ?? 0) >= WET_MM);
  const meta = [farm.region, farm.area_hectares && `${farm.area_hectares} ha`, `${fields.length} ${fields.length === 1 ? "field" : "fields"}`]
    .filter(Boolean)
    .join(" · ");

  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <header className="flex animate-rise flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-1">
            <Link to="/" className="text-small text-ink-muted hover:text-ink">
              Farms /
            </Link>
            <h1 className="text-h2">{farm.name}</h1>
            <span className="text-small text-ink-muted">{meta}</span>
          </div>
          <Button onClick={() => setLogOpen(true)} disabled={fields.length === 0}>
            Log observation
          </Button>
        </header>

        <ModelStoppedCard />

        <section className="relative animate-rise overflow-hidden rounded-xl bg-raised [animation-delay:80ms]">
          <picture>
            <source srcSet={`/twin/farm-${wet ? "rain" : "dry"}.webp`} type="image/webp" />
            <img
              src={`/twin/farm-${wet ? "rain" : "dry"}.jpg`}
              alt={wet ? "Example farm twin in rain, shown because this farm logged heavy rain recently" : "Example farm twin in dry weather"}
              className="aspect-[16/7] w-full object-cover"
            />
          </picture>
          <span className="absolute top-4 left-4 rounded-pill bg-raised/90 px-3 py-1 text-caption text-ink-muted">
            {/* a shared example scene until the twin draws this farm's own fields (#24) */}
            Example twin{wet ? " · wet after recent rain" : ""}
          </span>
        </section>

        {fields.length === 0 ? (
          <div className="rounded-lg bg-raised p-6 text-body text-ink-muted">
            This farm has no fields yet. <Link to="/setup" className="text-brand underline">Add a field and what's planted</Link> to see stages and risks.
          </div>
        ) : (
          <section className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(300px,1fr))]">
            {fields.map((f) => (
              <FieldCard key={f.id} field={f} />
            ))}
          </section>
        )}

        <section className="grid items-start gap-4 lg:grid-cols-[1.2fr_1fr]">
          <RainChart days={rainfall} />
          <RiskList risks={risks} />
        </section>

        <AskPanel farmId={farmId} context={askContext(load.data)} onOpenSource={setChunk} />
      </div>

      <LogSheet
        open={logOpen}
        fields={fields}
        onClose={() => setLogOpen(false)}
        onSaved={(obs, label) => {
          setLogOpen(false);
          setUndo({ obs, label });
          void refresh();
        }}
      />

      {undo && (
        <div role="status" className="fixed inset-x-4 bottom-6 z-50 mx-auto flex max-w-md animate-rise items-center justify-between gap-4 rounded-pill bg-ink py-2 pr-2 pl-5 text-small text-on-ink shadow-float">
          <span>{undo.label} logged. Stages and risks are updated.</span>
          <button type="button" onClick={() => void undoLast()} className="min-h-11 rounded-pill bg-on-ink/15 px-4 hover:bg-on-ink/25">
            Undo
          </button>
        </div>
      )}

      <SourceDrawer chunk={chunk} onClose={() => setChunk(null)} />
    </AppShell>
  );
}

/** The chips above the question: what the answer will take into account. */
function askContext({ fields, risks }: FarmDashboardData): AskContextChip[] {
  const chips: AskContextChip[] = fields.flatMap((f) =>
    f.plantings.map((p) => ({ key: `p${p.id}`, crop: p.crop, label: `${cropLabel(p.crop)} · ${stageLabel(p.stage)}` })),
  );
  if (risks[0]) chips.push({ key: "risk", risk: risks[0].severity, label: risks[0].title });
  return chips;
}
