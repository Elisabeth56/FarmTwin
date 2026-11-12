import { useModel } from "../lib/model";

const LOOK = {
  ready: { dot: "bg-risk-low", text: "Model ready · offline" },
  starting: { dot: "bg-risk-medium animate-pulse", text: "Model starting…" },
  stopped: { dot: "bg-risk-high", text: "Model stopped" },
  not_set_up: { dot: "bg-ink-faint", text: "Model not set up" },
} as const;

/** Sidebar card: the model's state at a glance. */
export default function ModelStatusCard() {
  const { status } = useModel();
  const look = status ? LOOK[status.state] : { dot: "bg-ink-faint", text: "Checking the model…" };
  return (
    <div className="flex flex-col gap-1 rounded-md bg-surface p-3 text-caption">
      <span role="status" className="flex items-center gap-2 text-ink">
        <span aria-hidden className={`size-2 rounded-pill ${look.dot}`} />
        {look.text}
      </span>
      <span className="text-ink-muted">Your farm data stays on this computer.</span>
    </div>
  );
}
