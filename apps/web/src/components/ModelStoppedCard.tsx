import { useState } from "react";
import { useModel } from "../lib/model";
import Button from "./Button";

/** Shown on the farm screen when the model is down. Everything except questions keeps working. */
export default function ModelStoppedCard() {
  const { status, restart, restarting } = useModel();
  const [dismissed, setDismissed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!status || status.state !== "stopped" || dismissed) return null;

  return (
    <section role="alert" className="flex animate-rise flex-col gap-4 rounded-xl bg-raised p-6 md:p-8">
      <span className="inline-flex items-center gap-2 text-small text-ink-muted">
        <span aria-hidden className="size-2 rounded-pill bg-risk-high" />
        Questions are paused
      </span>
      <h2 className="text-h2">The model stopped.</h2>
      <p className="max-w-xl text-lead text-ink-muted">{status.detail || "The model stopped unexpectedly."}</p>
      <p className="max-w-xl text-body text-ink-muted">Your farms, logs and risk checks still work. Only questions are paused.</p>
      {!status.managed && (
        <p className="max-w-xl text-small text-ink-muted">FarmTwin didn't start the model here. Start llama-server again, and this card will go away by itself.</p>
      )}
      {error && <p className="text-small text-risk-high">{error}</p>}
      <div className="flex flex-wrap gap-2">
        {status.managed && (
          <Button
            disabled={restarting}
            onClick={() => {
              setError(null);
              restart().catch((e: Error) => setError(e.message));
            }}
          >
            {restarting ? "Restarting…" : "Restart the model"}
          </Button>
        )}
        <Button variant="quiet" onClick={() => setDismissed(true)}>
          Keep working without answers
        </Button>
      </div>
    </section>
  );
}
