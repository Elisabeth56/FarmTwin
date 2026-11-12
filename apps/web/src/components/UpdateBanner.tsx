import { useEffect, useState } from "react";
import { inDesktopApp } from "../lib/desktop";

type Update = { version: string; install: () => Promise<void> };

/** In the desktop app: checks for a new version once per launch and asks before installing.
 *  Offline, or if anything goes wrong, it stays silent. Farm data and models live outside the
 *  app folder, so an update never touches them. */
export default function UpdateBanner() {
  const [update, setUpdate] = useState<Update | null>(null);
  const [installing, setInstalling] = useState(false);

  useEffect(() => {
    if (!inDesktopApp()) return;
    (async () => {
      try {
        const { check } = await import("@tauri-apps/plugin-updater");
        const found = await check();
        if (!found) return;
        setUpdate({
          version: found.version,
          install: async () => {
            await found.downloadAndInstall();
            const { relaunch } = await import("@tauri-apps/plugin-process");
            await relaunch();
          },
        });
      } catch {
        // offline or the release feed is unreachable: try again next launch
      }
    })();
  }, []);

  if (!update) return null;
  return (
    <div role="status" className="fixed inset-x-4 top-4 z-50 mx-auto flex max-w-xl animate-rise items-center justify-between gap-4 rounded-pill bg-ink py-2 pr-2 pl-5 text-small text-on-ink shadow-float">
      <span>FarmTwin {update.version} is ready. Your farms and model stay as they are.</span>
      <span className="flex gap-1">
        <button type="button" onClick={() => setUpdate(null)} className="min-h-11 rounded-pill px-4 hover:bg-on-ink/15">
          Later
        </button>
        <button
          type="button"
          disabled={installing}
          onClick={() => {
            setInstalling(true);
            update.install().catch(() => setInstalling(false));
          }}
          className="min-h-11 rounded-pill bg-brand-tint px-4 text-ink disabled:opacity-60"
        >
          {installing ? "Installing…" : "Install and restart"}
        </button>
      </span>
    </div>
  );
}
