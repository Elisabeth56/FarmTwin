import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import AskPanel, { type AskContextChip } from "../components/AskPanel";
import Button from "../components/Button";
import FarmTwin3D, { canDraw3D } from "../components/FarmTwin3D";
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
import { recall, remember } from "../lib/storage";

type Load =
  | { state: "loading" }
  | { state: "error"; message: string }
  | { state: "ready"; data: FarmDashboardData };
type Undo = { obs: Observation; label: string };

/** Rain at or above this in the last three days switches the twin to its wet look. */
const WET_MM = 20;

export default function FarmDashboard() {
  const farmId = Number(useParams<{ id: string }>().id);
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [logOpen, setLogOpen] = useState(false);
  const [logField, setLogField] = useState<number | null>(null);
  const [draft, setDraft] = useState<{ text: string; at: number } | null>(null);
  const [undo, setUndo] = useState<Undo | null>(null);
  const [chunk, setChunk] = useState<CitedChunk | null>(null);
  // the still picture is the default; the 3D choice is remembered across farms and launches
  const [has3D] = useState(canDraw3D);
  const [show3D, setShow3D] = useState(() => recall("farm.view") === "3d");
  const toggle3D = () => {
    remember("farm.view", show3D ? "still" : "3d");
    setShow3D(!show3D);
  };

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
          <div
            aria-busy="true"
            aria-label="Loading farm"
            className="flex flex-col gap-6"
          >
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
  const meta = [
    farm.region,
    farm.area_hectares && `${farm.area_hectares} ha`,
    `${fields.length} ${fields.length === 1 ? "field" : "fields"}`,
  ]
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
          <Button
            onClick={() => setLogOpen(true)}
            disabled={fields.length === 0}
          >
            Log observation
          </Button>
        </header>

        <ModelStoppedCard />

        <section className="relative animate-rise overflow-hidden rounded-xl bg-raised [animation-delay:80ms]">
          {has3D && show3D && fields.some((f) => f.plantings.length > 0) ? (
            <FarmTwin3D
              fields={fields}
              risks={risks}
              wet={wet}
              onLog={(id) => {
                setLogField(id);
                setLogOpen(true);
              }}
              onAsk={(text) => setDraft({ text, at: Date.now() })}
            />
          ) : (
            <>
              <picture>
                <source
                  srcSet={`/twin/farm-${wet ? "rain" : "dry"}.webp`}
                  type="image/webp"
                />
                <img
                  src={`/twin/farm-${wet ? "rain" : "dry"}.jpg`}
                  alt={
                    wet
                      ? "Example farm twin in rain, shown because this farm logged heavy rain recently"
                      : "Example farm twin in dry weather"
                  }
                  className="aspect-[16/7] w-full object-cover"
                />
              </picture>
              <span className="absolute top-4 left-4 rounded-pill bg-raised/90 px-3 py-1 text-caption text-ink-muted">
                Example twin{wet ? " · wet after recent rain" : ""}
              </span>
            </>
          )}
          {has3D && fields.some((f) => f.plantings.length > 0) && (
            <button
              type="button"
              aria-label={show3D ? "Show picture" : "Show this farm in 3D"}
              onClick={toggle3D}
              className="absolute top-3 right-3 z-20 inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-pill bg-raised/90 px-3 text-small text-ink shadow-float hover:bg-raised focus-visible:outline-2 focus-visible:outline-brand sm:px-4"
            >
              {/* on phones the 3D view's risk badge needs the room, so "Show picture" is an icon there */}
              {show3D && (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 18 18"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinejoin="round"
                  aria-hidden
                  className="sm:hidden"
                >
                  <rect x="2.5" y="3.5" width="13" height="11" rx="2.5" />
                  <path d="m3 13 4-4 3 3 2-2 3.5 3.5" />
                </svg>
              )}
              <span className={show3D ? "hidden sm:inline" : ""}>
                {show3D ? "Show picture" : "Show this farm in 3D"}
              </span>
            </button>
          )}
        </section>

        {fields.length === 0 ? (
          <div className="rounded-lg bg-raised p-6 text-body text-ink-muted">
            This farm has no fields yet.{" "}
            <Link to="/setup" className="text-brand underline">
              Add a field and what's planted
            </Link>{" "}
            to see stages and risks.
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

        <AskPanel
          farmId={farmId}
          context={askContext(load.data)}
          onOpenSource={setChunk}
          draft={draft}
        />
      </div>

      <LogSheet
        open={logOpen}
        fields={fields}
        key={logField ?? "any"}
        initialField={logField}
        onClose={() => {
          setLogOpen(false);
          setLogField(null);
        }}
        onSaved={(obs, label) => {
          setLogOpen(false);
          setUndo({ obs, label });
          void refresh();
        }}
      />

      {undo && (
        <div
          role="status"
          className="fixed inset-x-4 bottom-6 z-50 mx-auto flex max-w-md animate-rise items-center justify-between gap-4 rounded-pill bg-ink py-2 pr-2 pl-5 text-small text-on-ink shadow-float"
        >
          <span>{undo.label} logged. Stages and risks are updated.</span>
          <button
            type="button"
            onClick={() => void undoLast()}
            className="min-h-11 rounded-pill bg-on-ink/15 px-4 hover:bg-on-ink/25"
          >
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
    f.plantings.map((p) => ({
      key: `p${p.id}`,
      crop: p.crop,
      label: `${cropLabel(p.crop)} · ${stageLabel(p.stage)}`,
    })),
  );
  if (risks[0])
    chips.push({ key: "risk", risk: risks[0].severity, label: risks[0].title });
  return chips;
}
