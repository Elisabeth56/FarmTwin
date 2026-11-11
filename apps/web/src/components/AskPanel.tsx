import { useEffect, useRef, useState } from "react";
import Button from "./Button";
import Card from "./Card";
import MicButton from "./MicButton";
import {
  askQuestionStream,
  type CitedChunk,
  type Recommendation,
  type StreamEvent,
} from "../lib/api";

export type AskPanelProps = {
  farmId: number;
  onCitationClick: (chunk: CitedChunk) => void;
  onNewRecommendations: (recs: Recommendation[]) => void;
};

type StreamingResponse = {
  narrative: string;
  recommendations: Recommendation[];
  cited_chunks: CitedChunk[];
  model_name?: string;
  timing_ms?: {
    prompt_ms?: number;
    generation_ms?: number;
    llm_wallclock_ms?: number;
    total_ms: number;
  };
  streaming: boolean;
  gotFirstToken: boolean;
  cancelled?: boolean;
};

type Turn = {
  id: number;
  question: string;
  status: "streaming" | "done" | "error";
  response?: StreamingResponse;
  error?: string;
};

const CITATION_RE = /\[K(\d+)\]/g;

const PARTIAL_FENCE_RE = /`{1,3}(?:j(?:s(?:o(?:n)?)?)?)?\s*$/;

export function stripJsonBlock(narrative: string): {
  visibleText: string;
  jsonStarted: boolean;
} {
  if (!narrative) return { visibleText: "", jsonStarted: false };

  const fullIdx = narrative.indexOf("```json");
  if (fullIdx !== -1) {
    return { visibleText: narrative.slice(0, fullIdx).trimEnd(), jsonStarted: true };
  }

  const partialMatch = narrative.match(PARTIAL_FENCE_RE);
  if (partialMatch && partialMatch.index !== undefined) {
    return {
      visibleText: narrative.slice(0, partialMatch.index).trimEnd(),
      jsonStarted: false,
    };
  }

  return { visibleText: narrative, jsonStarted: false };
}

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
        className="inline-flex items-center rounded bg-brand-tint text-brand text-[11px] font-medium px-1.5 py-0.5 mx-0.5 hover:bg-brand hover:text-on-ink transition-colors align-baseline"
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
  const [micError, setMicError] = useState<string | null>(null);
  const [micRecording, setMicRecording] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const micErrorTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!micError) return;
    if (micErrorTimerRef.current !== null) {
      window.clearTimeout(micErrorTimerRef.current);
    }
    micErrorTimerRef.current = window.setTimeout(() => {
      setMicError(null);
      micErrorTimerRef.current = null;
    }, 5000);
    return () => {
      if (micErrorTimerRef.current !== null) {
        window.clearTimeout(micErrorTimerRef.current);
        micErrorTimerRef.current = null;
      }
    };
  }, [micError]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [turns]);

  function updateTurn(id: number, updater: (t: Turn) => Turn) {
    setTurns((prev) => prev.map((t) => (t.id === id ? updater(t) : t)));
  }

  async function submit(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    const id = Date.now();
    setBusy(true);
    setInput("");
    const initialResponse: StreamingResponse = {
      narrative: "",
      recommendations: [],
      cited_chunks: [],
      streaming: true,
      gotFirstToken: false,
    };
    setTurns((prev) => [
      ...prev,
      { id, question: q, status: "streaming", response: initialResponse },
    ]);

    const controller = new AbortController();
    abortRef.current = controller;

    const handleEvent = (event: StreamEvent) => {
      if (event.type === "ready") {
        updateTurn(id, (t) => ({
          ...t,
          response: t.response
            ? { ...t.response, cited_chunks: event.cited_chunks }
            : t.response,
        }));
      } else if (event.type === "token") {
        updateTurn(id, (t) => ({
          ...t,
          response: t.response
            ? {
                ...t.response,
                narrative: t.response.narrative + event.content,
                gotFirstToken: true,
              }
            : t.response,
        }));
      } else if (event.type === "recommendation_ready") {
        updateTurn(id, (t) => ({
          ...t,
          status: "done",
          response: t.response
            ? {
                ...t.response,
                narrative: event.narrative || t.response.narrative,
                recommendations: event.recommendations,
                cited_chunks: event.cited_chunks ?? t.response.cited_chunks,
                model_name: event.model_name,
                timing_ms: event.timing_ms,
                streaming: false,
              }
            : t.response,
        }));
        if (event.recommendations && event.recommendations.length > 0) {
          onNewRecommendations(event.recommendations);
        }
      } else if (event.type === "error") {
        updateTurn(id, (t) => ({
          ...t,
          status: "error",
          error: event.message,
          response: t.response
            ? { ...t.response, streaming: false }
            : t.response,
        }));
      }
    };

    try {
      await askQuestionStream(
        { farm_id: farmId, question: q },
        handleEvent,
        controller.signal,
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Ask failed.";
      updateTurn(id, (t) => ({
        ...t,
        status: "error",
        error: message,
        response: t.response
          ? { ...t.response, streaming: false }
          : t.response,
      }));
    } finally {
      abortRef.current = null;
      setBusy(false);
    }
  }

  function stopGenerating() {
    const controller = abortRef.current;
    if (!controller) return;
    controller.abort();
    abortRef.current = null;
    setTurns((prev) =>
      prev.map((t) =>
        t.status === "streaming"
          ? {
              ...t,
              status: "done",
              response: t.response
                ? { ...t.response, streaming: false, cancelled: true }
                : t.response,
            }
          : t,
      ),
    );
    setBusy(false);
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
      <div className="text-caption uppercase tracking-wide text-ink-faint">
        Ask FarmTwin
      </div>
      <div className="text-small text-ink-muted mt-1">
        Get advice grounded in your farm's state and local agricultural
        knowledge.
      </div>

      <div
        ref={scrollRef}
        className="mt-4 max-h-[500px] overflow-y-auto flex flex-col gap-4 pr-1"
      >
        {turns.length === 0 && (
          <div className="text-small text-ink-muted bg-ground rounded-md p-4">
            Try asking: <em>"What should I do this week?"</em> or{" "}
            <em>"Is my crop at risk from recent weather?"</em>
          </div>
        )}

        {turns.map((turn) => (
          <div key={turn.id} className="flex flex-col gap-3">
            <div className="self-end max-w-[85%] bg-brand-tint text-ink rounded-lg rounded-br-sm px-3 py-2 text-small">
              {turn.question}
            </div>

            {(turn.status === "streaming" || turn.status === "done") &&
              turn.response &&
              (() => {
                const { visibleText, jsonStarted } = stripJsonBlock(
                  turn.response.narrative,
                );
                const isStreaming = turn.status === "streaming";
                const showCursor = isStreaming && !jsonStarted;
                const showPrepRecs =
                  isStreaming &&
                  jsonStarted &&
                  turn.response.recommendations.length === 0;
                return (
                  <div className="text-small text-ink leading-relaxed">
                    {isStreaming && !turn.response.gotFirstToken ? (
                      <div className="animate-pulse text-ink-muted">
                        Preparing context…
                      </div>
                    ) : (
                      <div className="whitespace-pre-wrap">
                        {renderNarrativeWithCitations(
                          visibleText,
                          turn.response.cited_chunks,
                          onCitationClick,
                        )}
                        {showCursor && (
                          <span
                            className="inline-block w-[7px] h-[14px] ml-0.5 bg-brand align-[-2px] animate-pulse"
                            aria-hidden="true"
                          />
                        )}
                      </div>
                    )}

                    {showPrepRecs && (
                      <div className="text-small text-ink-faint animate-pulse mt-3">
                        Preparing recommendations…
                      </div>
                    )}

                    {turn.status === "done" && turn.response.cancelled && (
                      <div className="text-[11px] text-ink-faint mt-2 italic">
                        Generation cancelled by user.
                      </div>
                    )}

                    {turn.status === "done" && turn.response.model_name && (
                      <div className="text-[11px] text-ink-faint mt-3">
                        Model: {turn.response.model_name} · Generated in{" "}
                        {formatDuration(turn.response.timing_ms?.total_ms)}
                      </div>
                    )}
                  </div>
                );
              })()}

            {turn.status === "error" && turn.error && (
              <ErrorMessage message={turn.error} onRetry={() => retry(turn)} />
            )}
          </div>
        ))}
      </div>

      <div className="mt-4 flex flex-col gap-2 border-t border-hairline pt-4">
        <textarea
          className="w-full rounded-md border border-hairline bg-raised px-4 py-2.5 text-ink placeholder:text-ink-faint focus:border-brand focus:ring-1 focus:ring-brand outline-none transition-colors min-h-[60px] resize-none"
          placeholder="Ask a question about your farm…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={busy}
        />
        {busy && (
          <div className="text-[11px] text-ink-faint">
            This can take 2–4 minutes on local hardware. Grounded, offline
            reasoning is slow but private — tokens will appear as they're
            generated.
          </div>
        )}
        <div className="flex items-center gap-2 flex-wrap">
          <MicButton
            onTranscript={(text) => {
              setInput(text);
              setMicError(null);
            }}
            onError={(message) => setMicError(message)}
            onBusyChange={setMicRecording}
            disabled={busy}
          />
          {busy ? (
            <Button
              className="flex-1"
              onClick={stopGenerating}
              variant="secondary"
            >
              Stop generating
            </Button>
          ) : (
            <Button
              className="flex-1"
              onClick={() => submit(input)}
              disabled={!input.trim() || micRecording}
            >
              Send
            </Button>
          )}
        </div>
        {micError && (
          <div
            role="alert"
            className="text-[11px] text-risk-high bg-risk-high/5 border border-risk-high/30 rounded-sm px-2 py-1.5"
          >
            {micError}
          </div>
        )}
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
    <div className="rounded-md border border-risk-high/30 bg-risk-high/5 p-3">
      <div className="text-small font-medium text-risk-high">
        {isServerDown
          ? "Local model not available"
          : isTimeout
            ? "Model took too long"
            : "Something went wrong"}
      </div>
      <div className="text-small text-ink-muted mt-1">
        {isServerDown
          ? "Start llama-server first."
          : isTimeout
            ? "This can happen when other apps are competing for CPU. Try closing other apps and asking again."
            : message}
      </div>
      {isServerDown && (
        <pre className="mt-2 text-[11px] bg-raised border border-hairline rounded-sm p-2 overflow-x-auto whitespace-pre-wrap font-mono text-ink">
          cd ~/dev/tools/llama.cpp && ./build/bin/llama-server \
            --model ~/farmtwin-models/qwen2.5-3b-instruct-q4_k_m.gguf \
            --host 127.0.0.1 --port 8080 --ctx-size 4096 \
            --threads 4 --load-mode mlock
        </pre>
      )}
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 text-small text-brand hover:underline"
      >
        Retry
      </button>
    </div>
  );
}
