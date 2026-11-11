import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { getModelStatus, restartModel, type ModelStatus } from "./api";

// polled often enough that a crash shows within 5 seconds, rarely enough to cost nothing
const POLL_MS = 3000;

type ModelContext = {
  status: ModelStatus | null;
  refresh: () => void;
  restart: () => Promise<void>;
  restarting: boolean;
};

const Context = createContext<ModelContext>({
  status: null,
  refresh: () => {},
  restart: async () => {},
  restarting: false,
});

export function ModelStatusProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<ModelStatus | null>(null);
  const [restarting, setRestarting] = useState(false);

  const refresh = useCallback(() => {
    getModelStatus()
      .then(setStatus)
      .catch(() => setStatus({ state: "stopped", managed: false, detail: "FarmTwin's background service isn't answering." }));
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, POLL_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  const restart = useCallback(async () => {
    setRestarting(true);
    try {
      setStatus(await restartModel());
    } finally {
      setRestarting(false);
    }
  }, []);

  return <Context.Provider value={{ status, refresh, restart, restarting }}>{children}</Context.Provider>;
}

export function useModel(): ModelContext {
  return useContext(Context);
}
