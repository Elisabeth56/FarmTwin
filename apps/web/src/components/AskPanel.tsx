import { useEffect, useRef, useState, type ReactNode } from "react";
import { askQuestionStream, type AnswerKind, type CitedChunk, type Recommendation } from "../lib/api";
import { cropColor, cropLabel } from "../lib/crops";
import { recall, remember } from "../lib/storage";
import Button from "./Button";
import MicButton from "./MicButton";

export type AskContextChip = { key: string; label: string; crop?: string; risk?: "high" | "medium" | "low" };

type Turn = {
  question: string;
  status: "working" | "done" | "stopped" | "error";
  progress: string;
  text: string;
  kind: AnswerKind;
  sources: CitedChunk[];
  cards: Recommendation[];
  ids: number[];
  error?: string;
};

type AskPanelProps = {
  farmId: number;
  context: AskContextChip[];
  onOpenSource: (chunk: CitedChunk) => void;
};

const RISK_DOT = { high: "bg-risk-high", medium: "bg-risk-medium", low: "bg-risk-low" } as const;
const SUGGESTIONS = ["What should I do this week?", "Is my crop at risk from the recent weather?"];

/** Ask about this farm. The answer streams in, cites numbered sources and ends with a checklist. */
export default function AskPanel({ farmId, context, onOpenSource }: AskPanelProps) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [micError, setMicError] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);
  const working = turns.at(-1)?.status === "working";

  useEffect(() => () => abort.current?.abort(), []);

  const update = (patch: (t: Turn) => Partial<Turn>) =>
    setTurns((all) => all.map((t, i) => (i === all.length - 1 ? { ...t, ...patch(t) } : t)));

  const ask = async (question: string) => {
    const q = question.trim();
    if (q.length < 3 || working) return;
    setInput("");
    // the first progress line is local, so it shows the moment the question is sent
    setTurns((all) => [
      ...all,
      { question: q, status: "working", progress: "Sending your question…", text: "", kind: "answer", sources: [], cards: [], ids: [] },
    ]);
    const controller = new AbortController();
    abort.current = controller;

    await askQuestionStream(
      { farm_id: farmId, question: q },
      (event) => {
        if (event.type === "progress") update(() => ({ progress: event.message }));
        else if (event.type === "token") update((t) => ({ text: t.text + event.content, progress: "Writing the answer…" }));
        else if (event.type === "recommendation_ready")
          update(() => ({
            status: "done",
            kind: event.kind,
            text: event.narrative,
            sources: event.kind === "answer" ? (event.cited_chunks ?? []) : [],
            cards: event.recommendations,
            ids: event.saved_recommendation_ids,
          }));
        else if (event.type === "error") update(() => ({ status: "error", error: event.message }));
      },
      controller.signal,
    );
    abort.current = null;
  };

  const stop = () => {
    abort.current?.abort();
    update(() => ({ status: "stopped" }));
  };

  return (
    <div className="flex animate-rise flex-col gap-5 rounded-lg bg-raised p-5">
      <div className="flex flex-col gap-1">
        <span className="text-h3">Ask about this farm</span>
        <span className="text-small text-ink-muted">Answers use your logs, the risks above and FarmTwin's farming guides.</span>
      </div>

      {context.length > 0 && (
        <div aria-label="What the answer will know" className="flex flex-wrap gap-2">
          {context.map((c) => (
            <span key={c.key} className="inline-flex items-center gap-2 rounded-pill bg-surface px-3 py-1 text-caption text-ink-muted">
              {c.crop && <span aria-hidden className="size-2 rounded-pill" style={{ background: cropColor(c.crop) }} />}
              {c.risk && <span aria-hidden className={`size-2 rounded-pill ${RISK_DOT[c.risk]}`} />}
              {c.label}
            </span>
          ))}
        </div>
      )}

      {turns.map((t, i) => (
        <TurnView key={i} turn={t} onOpenSource={onOpenSource} />
      ))}

      {turns.length === 0 && (
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <Button key={s} variant="quiet" onClick={() => void ask(s)}>
              {s}
            </Button>
          ))}
        </div>
      )}

      <form
        className="flex flex-col gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void ask(input);
        }}
      >
        <label className="sr-only" htmlFor="ask-input">
          Your question
        </label>
        <textarea
          id="ask-input"
          rows={2}
          value={input}
          maxLength={500}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void ask(input);
            }
          }}
          placeholder="Ask in English or Pidgin…"
          className="rounded-md bg-surface px-4 py-3 text-body text-ink ring-1 ring-hairline ring-inset outline-none placeholder:text-ink-muted"
        />
        {micError && <p className="text-small text-risk-high">{micError}</p>}
        <div className="flex items-center gap-2">
          <MicButton
            disabled={working}
            onTranscript={(text) => {
              setInput(text);
              setMicError(null);
            }}
            onError={setMicError}
          />
          {working ? (
            <Button type="button" variant="secondary" onClick={stop} className="flex-1">
              Stop
            </Button>
          ) : (
            <Button type="submit" disabled={input.trim().length < 3} className="flex-1">
              Ask
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}

function TurnView({ turn, onOpenSource }: { turn: Turn; onOpenSource: (c: CitedChunk) => void }) {
  const visible = withoutJson(turn.text);
  return (
    <div className="flex flex-col gap-3 border-t border-hairline pt-4">
      <p className="self-end rounded-md bg-brand-tint px-4 py-2 text-body">{turn.question}</p>

      {turn.status === "working" && (
        <p role="status" className="flex items-center gap-2 text-small text-ink-muted">
          <span aria-hidden className="size-2 animate-pulse rounded-pill bg-brand" />
          {turn.progress}
        </p>
      )}

      {visible && (
        <p className={`text-body whitespace-pre-wrap ${turn.kind === "answer" ? "text-ink" : "text-ink-muted"}`}>
          {withCitations(visible, turn.sources, onOpenSource)}
        </p>
      )}

      {turn.status === "stopped" && <p className="text-small text-ink-muted">Stopped. Ask again whenever you're ready.</p>}
      {turn.status === "error" && <p className="text-small text-risk-high">{turn.error}</p>}

      {turn.status === "done" && turn.cards.length > 0 && <Checklist cards={turn.cards} ids={turn.ids} />}

      {turn.status === "done" && turn.sources.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-caption text-ink-muted">Sources</span>
          <ol className="flex flex-col gap-1">
            {turn.sources.map((c, i) => (
              <li key={c.chunk_id}>
                <button
                  type="button"
                  onClick={() => onOpenSource(c)}
                  className="flex min-h-11 w-full items-center gap-3 rounded-md bg-surface px-3 text-left text-small hover:bg-ink/5"
                >
                  <span className="tabular grid size-6 shrink-0 place-items-center rounded-pill bg-ink text-caption text-on-ink">{i + 1}</span>
                  <span className="flex flex-col">
                    <span>{c.chunk_title}</span>
                    <span className="text-caption text-ink-muted">
                      {c.source_org} · {cropLabel(c.crop)}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

/** "Do this week" for urgent cards, "Keep an eye on" for the rest. Ticks are remembered on this device. */
function Checklist({ cards, ids }: { cards: Recommendation[]; ids: number[] }) {
  const keyFor = (i: number) => `ft.done.${ids[i] ?? "x"}`;
  const [done, setDone] = useState<Record<number, boolean>>(() =>
    Object.fromEntries(cards.map((_, i) => [i, recall(keyFor(i)) === "1"])),
  );
  const toggle = (i: number) => {
    setDone((d) => ({ ...d, [i]: !d[i] }));
    if (ids[i] !== undefined) remember(keyFor(i), done[i] ? "0" : "1");
  };
  const groups: [string, number[]][] = [
    ["Do this week", cards.map((_, i) => i).filter((i) => cards[i].when_urgency !== "monitor")],
    ["Keep an eye on", cards.map((_, i) => i).filter((i) => cards[i].when_urgency === "monitor")],
  ];
  return (
    <div className="flex flex-col gap-3 rounded-md bg-surface p-4">
      {groups
        .filter(([, items]) => items.length > 0)
        .map(([title, items]) => (
          <div key={title} className="flex flex-col gap-2">
            <span className="text-caption text-ink-muted">{title}</span>
            {items.map((i) => (
              <label key={i} className="flex cursor-pointer items-start gap-3">
                <input type="checkbox" checked={!!done[i]} onChange={() => toggle(i)} className="mt-1 size-5 shrink-0 accent-[var(--brand)]" />
                <span className="flex flex-col">
                  <span className={`text-body ${done[i] ? "text-ink-muted line-through" : ""}`}>
                    {cards[i].what}
                    {cards[i].when_urgency === "immediate" && <span className="ml-2 text-caption text-risk-high">today</span>}
                  </span>
                  <span className="text-small text-ink-muted">{cards[i].why}</span>
                </span>
              </label>
            ))}
          </div>
        ))}
    </div>
  );
}

/** Hides the recommendations block while it streams in. */
function withoutJson(text: string): string {
  const fence = text.indexOf("```");
  return (fence >= 0 ? text.slice(0, fence) : text).trimEnd();
}

/** Turns [K3] into a numbered button for the matching cited source. Unknown IDs are dropped. */
function withCitations(text: string, sources: CitedChunk[], open: (c: CitedChunk) => void): ReactNode[] {
  return text.split(/(\s?\[K\d+\])/g).map((part, i) => {
    const m = part.match(/^\s?\[K(\d+)\]$/);
    if (!m) return part;
    const n = sources.findIndex((s) => s.citation === `K${m[1]}`);
    if (n < 0) return null;
    return (
      <button
        key={i}
        type="button"
        onClick={() => open(sources[n])}
        aria-label={`Source ${n + 1}: ${sources[n].chunk_title}`}
        className="mx-0.5 inline-grid size-5 place-items-center rounded-pill bg-ink align-text-top text-caption text-on-ink"
      >
        {n + 1}
      </button>
    );
  });
}
