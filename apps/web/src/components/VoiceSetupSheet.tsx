import { useCallback, useEffect, useState } from "react";
import { getSetup, importModel, pauseModelDownload, startModelDownload, type SetupProgress } from "../lib/api";
import { pickModelFile } from "../lib/desktop";
import Button from "./Button";
import Sheet from "./Sheet";

const MB = 1_000_000;
const mb = (bytes: number) => Math.round(bytes / MB);

/** Gets the optional voice model the same way as the AI model: download or a file from a flash drive. */
export default function VoiceSetupSheet({ open, onClose, onReady }: { open: boolean; onClose: () => void; onReady: () => void }) {
  const [p, setP] = useState<SetupProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [path, setPath] = useState<string | null>(null);

  const poll = useCallback(() => getSetup("voice").then(setP).catch((e: Error) => setError(e.message)), []);

  useEffect(() => {
    if (!open) return;
    void poll();
    const timer = setInterval(poll, 1000);
    return () => clearInterval(timer);
  }, [open, poll]);

  useEffect(() => {
    if (p?.state === "ready") onReady();
  }, [p?.state, onReady]);

  const act = (work: () => Promise<SetupProgress>) => {
    setError(null);
    work().then(setP).catch((e: Error) => setError(e.message));
  };

  const chooseFile = async () => {
    const picked = await pickModelFile("voice");
    if (picked) act(() => importModel(picked, "voice"));
    else setPath(""); // no file picker outside the desktop app
  };

  const share = p?.total ? p.done / p.total : 0;
  // an error stays on screen until the user picks "Import a file instead"
  const busy = p && (["downloading", "verifying", "paused"].includes(p.state) || (p.state === "error" && path === null));

  return (
    <Sheet open={open} title="Turn on voice input" onClose={onClose}>
      <div className="flex flex-col gap-5">
        <p className="text-body text-ink-muted">
          Speak your question instead of typing it. Voice runs on this laptop and needs one more file, about {p ? mb(p.size) : 190} MB. English only for now.
        </p>

        {!busy && path === null && (
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => act(() => startModelDownload("voice"))}>Download</Button>
            <Button variant="secondary" onClick={() => void chooseFile()}>
              Import from a flash drive
            </Button>
          </div>
        )}

        {path !== null && !busy && (
          <form
            className="flex flex-col gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              e.stopPropagation(); // React bubbles through the portal to the ask form
              act(() => importModel(path, "voice"));
              setPath(null);
            }}
          >
            <label className="flex flex-col gap-2 text-small text-ink-muted">
              Full path to the .bin file
              <input
                autoFocus
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="/Volumes/FLASH/ggml-small.en-q5_1.bin"
                className="min-h-11 rounded-md bg-surface px-4 text-body text-ink ring-1 ring-hairline ring-inset placeholder:text-ink-muted"
              />
            </label>
            <div className="flex gap-2">
              <Button type="submit" disabled={!path.trim()}>
                Import
              </Button>
              <Button type="button" variant="quiet" onClick={() => setPath(null)}>
                Back
              </Button>
            </div>
          </form>
        )}

        {p && busy && (
          <div className="flex flex-col gap-3">
            {p.state !== "error" && (
              <div className="h-2 overflow-hidden rounded-pill bg-ink/5" role="progressbar" aria-label="Voice model" aria-valuenow={Math.floor(share * 100)} aria-valuemin={0} aria-valuemax={100}>
                <div className="h-full origin-left rounded-pill bg-brand transition-transform duration-500 ease-ui" style={{ transform: `scaleX(${share})` }} />
              </div>
            )}
            <p role="status" className={`text-small ${p.state === "error" ? "text-risk-high" : "text-ink-muted"}`}>
              {p.state === "error"
                ? p.error
                : p.state === "verifying"
                  ? "Checking the file."
                  : `${p.state === "paused" ? "Paused at " : ""}${mb(p.done)} MB of ${mb(p.total)} MB`}
            </p>
            <div className="flex gap-2">
              {p.state === "downloading" && (
                <Button variant="secondary" onClick={() => act(() => pauseModelDownload("voice"))}>
                  Pause
                </Button>
              )}
              {(p.state === "paused" || p.state === "error") && (
                <Button onClick={() => act(() => startModelDownload("voice"))}>{p.state === "paused" ? "Resume" : "Download"}</Button>
              )}
              {p.state === "error" && (
                <Button variant="quiet" onClick={() => setPath("")}>
                  Import a file instead
                </Button>
              )}
            </div>
          </div>
        )}

        {error && <p className="text-small text-risk-high">{error}</p>}
      </div>
    </Sheet>
  );
}
