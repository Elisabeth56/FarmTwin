import { useEffect, useState, type ReactNode } from "react";
import { getHealth } from "../lib/api";
import Logo from "./Logo";

/** Holds the app until the local API answers. On a cold start the backend takes a few seconds. */
export default function StartupGate({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    let stopped = false;
    const slowTimer = setTimeout(() => setSlow(true), 15_000);
    const attempt = () =>
      getHealth()
        .then(() => !stopped && setReady(true))
        .catch(() => !stopped && setTimeout(attempt, 400));
    attempt();
    return () => {
      stopped = true;
      clearTimeout(slowTimer);
    };
  }, []);

  if (ready) return <>{children}</>;
  return (
    <div className="grid h-full place-items-center" aria-busy="true">
      <div className="flex animate-rise flex-col items-center gap-4 text-center">
        <Logo />
        <p role="status" className="text-small text-ink-muted">
          {slow ? "Still starting. Older laptops can take up to a minute the first time." : "Starting FarmTwin…"}
        </p>
      </div>
    </div>
  );
}
