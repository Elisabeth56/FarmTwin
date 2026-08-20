import { useEffect, useRef, useState } from "react";
import Button from "./Button";
import Card from "./Card";
import {
  askQuestion,
  type AskResponse,
  type CitedChunk,
  type Recommendation,
} from "../lib/api";

export type AskPanelProps = {
  farmId: number;
  onCitationClick: (chunk: CitedChunk) => void;
  onNewRecommendations: (recs: Recommendation[]) => void;
};

type Turn = {
  id: number;
  question: string;
  status: "loading" | "done" | "error";
  response?: AskResponse;
  error?: string;
};

const CITATION_RE = /\[K(\d+)\]/g;

function formatDuration(ms?: number): string {
  if (!ms || ms <= 0) return "—";
  const totalSec = Math.round(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

function renderNarrativeWithCitations(
  narrative: string,
  chunks: CitedChunk[],
  onCitationClick: (chunk: CitedChunk) => void,
) {
  const chunkMap = new Map<string, CitedChunk>();
  for (const c of chunks) chunkMap.set(c.citation, c);

  const parts: Array<string | { citation: string }> = [];
  let last = 0;
  const re = new RegExp(CITATION_RE);
  let m: RegExpExecArray | null;
  while ((m = re.exec(narrative)) !== null) {
    if (m.index > last) parts.push(narrative.slice(last, m.index));
    parts.push({ citation: `K${m[1]}` });
    last = m.index + m[0].length;
  }
  if (last < narrative.length) parts.push(narrative.slice(last));

  return parts.map((part, i) => {
    if (typeof part === "string") {
      return <span key={i}>{part}</span>;
    }
    const chunk = chunkMap.get(part.citation);
    if (!chunk) {
      return (
        <span key={i} className="text-ink-faint">
          [{part.citation}]
        </span>
      );
    }
    return (
      <button
        key={i}
        type="button"
        onClick={() => onCitationClick(chunk)}
        className="inline-flex items-center rounded bg-primary-tint text-primary text-[11px] font-medium px-1.5 py-0.5 mx-0.5 hover:bg-primary hover:text-white transition-colors align-baseline"
        title={chunk.chunk_title}
      >
        {part.citation}
      </button>
    );
  });
}

export default function AskPanel({
  farmId,
  onCitationClick,
  onNewRecommendations,
}: AskPanelProps) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [turns]);

  async function submit(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    const id = Date.now();
    setBusy(true);
    setInput("");
    setTurns((prev) => [
      ...prev,
      { id, question: q, status: "loading" },
    ]);
    try {
      const resp = await askQuestion({ farm_id: farmId, question: q });
      setTurns((prev) =>
        prev.map((t) =>
          t.id === id ? { ...t, status: "done", response: resp } : t,
        ),
      );
      if (resp.recommendations && resp.recommendations.length > 0) {
        onNewRecommendations(resp.recommendations);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Ask failed.";
      setTurns((prev) =>
        prev.map((t) =>
          t.id === id ? { ...t, status: "error", error: message } : t,
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(input);
    }
  }

  function retry(turn: Turn) {
    if (busy) return;
    setTurns((prev) => prev.filter((t) => t.id !== turn.id));
    submit(turn.question);
  }

  return (
    <Card>
      <div className="text-xs uppercase tracking-wide text-ink-faint">
        Ask FarmTwin
      </div>
      <div className="text-sm text-ink-muted mt-1">
        Get advice grounded in your farm's state and local agricultural
        knowledge.
      </div>

      <div
        ref={scrollRef}
        className="mt-4 max-h-[500px] overflow-y-auto flex flex-col gap-4 pr-1"
      >
        {turns.length === 0 && (
          <div className="text-sm text-ink-muted bg-bg rounded-xl p-4">
            Try asking: <em>"What should I do this week?"</em> or{" "}
            <em>"Is my crop at risk from recent weather?"</em>
          </div>
        )}

        {turns.map((turn) => (
          <div key={turn.id} className="flex flex-col gap-3">
            <div className="self-end max-w-[85%] bg-primary-tint text-ink rounded-2xl rounded-br-sm px-3 py-2 text-sm">
              {turn.question}
            </div>

            {turn.status === "loading" && (
              <div className="text-sm text-ink-muted">
                <div className="animate-pulse font-medium text-ink">
                  FarmTwin is thinking…
                </div>
                <div className="text-xs text-ink-faint mt-1">
                  This can take 2–4 minutes on local hardware. Grounded,
                  offline reasoning is slow but private.
                </div>
              </div>
            )}

            {turn.status === "done" && turn.response && (
              <div className="text-sm text-ink leading-relaxed">
                <div className="whitespace-pre-wrap">
                  {renderNarrativeWithCitations(
                    turn.response.narrative,
                    turn.response.cited_chunks,
                    onCitationClick,
                  )}
                </div>
                <div className="text-[11px] text-ink-faint mt-3">
                  Model: {turn.response.model_name} · Generated in{" "}
                  {formatDuration(turn.response.timing_ms.total_ms)}
                </div>
              </div>
            )}

            {turn.status === "error" && turn.error && (
              <ErrorMessage message={turn.error} onRetry={() => retry(turn)} />
            )}
          </div>
        ))}
      </div>

      <div className="mt-4 flex flex-col gap-2 border-t border-border pt-4">
        <textarea
          className="w-full rounded-xl border border-border bg-white px-4 py-2.5 text-ink placeholder:text-ink-faint focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors min-h-[60px] resize-none"
          placeholder="Ask a question about your farm…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={busy}
        />
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled
            title="Voice input coming Day 5"
            className="rounded-xl border border-border bg-white text-ink-faint px-3 py-2 cursor-not-allowed"
            aria-label="Voice input (coming Day 5)"
          >
            🎤
          </button>
          <Button
            className="flex-1"
            onClick={() => submit(input)}
            disabled={busy || !input.trim()}
          >
            {busy ? "Sending…" : "Send"}
          </Button>
        </div>
      </div>
    </Card>
  );
}

function ErrorMessage({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  const isServerDown = /Local model not available/i.test(message);
  const isTimeout = /took too long/i.test(message);

  return (
    <div className="rounded-xl border border-risk-high/30 bg-risk-high/5 p-3">
      <div className="text-sm font-medium text-risk-high">
        {isServerDown
          ? "Local model not available"
          : isTimeout
            ? "Model took too long"
            : "Something went wrong"}
      </div>
      <div className="text-sm text-ink-muted mt-1">
        {isServerDown
          ? "Start llama-server first."
          : isTimeout
            ? "This can happen when other apps are competing for CPU. Try closing other apps and asking again."
            : message}
      </div>
      {isServerDown && (
        <pre className="mt-2 text-[11px] bg-white border border-border rounded-lg p-2 overflow-x-auto whitespace-pre-wrap font-mono text-ink">
          cd ~/dev/tools/llama.cpp && ./build/bin/llama-server \
            --model ~/farmtwin-models/qwen2.5-3b-instruct-q4_k_m.gguf \
            --host 127.0.0.1 --port 8080 --ctx-size 4096 \
            --threads 4 --load-mode mlock
        </pre>
      )}
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 text-sm text-primary hover:underline"
      >
        Retry
      </button>
    </div>
  );
}
