import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import Button from "../components/Button";
import { getSetup, importModel, pauseModelDownload, startModelDownload, type SetupProgress } from "../lib/api";
import { pickModelFile } from "../lib/desktop";
import { useModel } from "../lib/model";
import { remember } from "../lib/storage";

export const SETUP_SEEN = "ft.setup.seen";

const GB = 1024 ** 3;
const gb = (bytes: number) => (bytes / GB).toFixed(1);

/** First run: get the model by download or from a file. Farms and logs work without it. */
export default function ModelSetup() {
  const [p, setP] = useState<SetupProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pathInput, setPathInput] = useState<string | null>(null);
  const model = useModel();

  const poll = useCallback(() => getSetup().then(setP).catch((e: Error) => setError(e.message)), []);

  useEffect(() => {
    remember(SETUP_SEEN, "1");
    void poll();
    const timer = setInterval(poll, 1000);
    return () => clearInterval(timer);
  }, [poll]);

  useEffect(() => {
    if (p?.state === "ready") model.refresh();
  }, [p?.state, model]);

  const act = (work: () => Promise<SetupProgress>) => {
    setError(null);
    work().then(setP).catch((e: Error) => setError(e.message));
  };

  const chooseFile = async () => {
    const path = await pickModelFile();
    if (path) act(() => importModel(path));
    else setPathInput(""); // in a browser there's no file picker: ask for the path
  };

  const working = p && ["downloading", "verifying"].includes(p.state);
  const started = p && p.state !== "missing";

  return (
    <AppShell>
      <section className="flex min-h-[calc(100dvh-8rem)] animate-rise flex-col gap-8 rounded-xl bg-raised p-6 md:min-h-[calc(100dvh-5rem)] md:p-12">
        <ol className="flex flex-wrap gap-2 text-small" aria-label="Setup steps">
          <li className="rounded-pill bg-brand-tint px-3 py-1">1 · AI model</li>
          <li className="rounded-pill bg-ink/5 px-3 py-1 text-ink-muted">2 · First farm</li>
        </ol>

        {p?.state === "ready" ? (
          <Done name={p.model_name} />
        ) : (
          <>
            <div className="flex max-w-2xl flex-col gap-3">
              <h1 className="text-h2 md:text-h1">Get FarmTwin's AI model.</h1>
              <p className="text-lead text-ink-muted">
                It answers your questions on this laptop, so it needs to be here once. About 2 GB. Your farms, logs and risk checks work while you wait.
              </p>
            </div>

            {!started && pathInput === null && (
              <div className="grid gap-4 md:grid-cols-2">
                <Option
                  title="Download the model"
                  body="About 2 GB. Pauses and resumes if your connection drops. Wi-Fi is best."
                  action="Download"
                  onClick={() => act(startModelDownload)}
                />
                <Option
                  title="Import from a flash drive"
                  body="Pick the .gguf file copied from another laptop. No internet needed."
                  action="Choose the file"
                  secondary
                  onClick={() => void chooseFile()}
                />
              </div>
            )}

            {pathInput !== null && !working && p?.state !== "error" && (
              <form
                className="flex max-w-2xl flex-col gap-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  act(() => importModel(pathInput));
                }}
              >
                <label className="flex flex-col gap-2 text-small text-ink-muted">
                  Full path to the .gguf file
                  <input
                    autoFocus
                    value={pathInput}
                    onChange={(e) => setPathInput(e.target.value)}
                    placeholder="/Volumes/FLASH/qwen2.5-3b-instruct-q4_k_m.gguf"
                    className="min-h-11 rounded-md bg-surface px-4 text-body text-ink ring-1 ring-hairline ring-inset placeholder:text-ink-muted"
                  />
                </label>
                <div className="flex gap-2">
                  <Button type="submit" disabled={!pathInput.trim()}>
                    Import
                  </Button>
                  <Button type="button" variant="quiet" onClick={() => setPathInput(null)}>
                    Choose another way
                  </Button>
                </div>
              </form>
            )}

            {p && started && <Work p={p} onPause={() => act(pauseModelDownload)} onResume={() => act(startModelDownload)} onReset={() => setPathInput(null)} />}
            {error && <p className="text-small text-risk-high">{error}</p>}
          </>
        )}
      </section>
    </AppShell>
  );
}

function Option({ title, body, action, onClick, secondary = false }: { title: string; body: string; action: string; onClick: () => void; secondary?: boolean }) {
  return (
    <div className="flex flex-col justify-between gap-6 rounded-lg bg-surface p-6">
      <div className="flex flex-col gap-2">
        <span className="text-h3">{title}</span>
        <span className="text-body text-ink-muted">{body}</span>
      </div>
      <Button variant={secondary ? "secondary" : "primary"} onClick={onClick} className="self-start">
        {action}
      </Button>
    </div>
  );
}

function Work({ p, onPause, onResume, onReset }: { p: SetupProgress; onPause: () => void; onResume: () => void; onReset: () => void }) {
  const share = p.total ? p.done / p.total : 0;
  const label = {
    downloading: "Downloading the model",
    paused: "Download paused",
    verifying: "Checking the file",
    error: "That didn't work",
    missing: "",
    ready: "",
  }[p.state];
  const meta =
    p.state === "verifying"
      ? "Making sure it's the right model and it isn't damaged."
      : p.state === "error"
        ? p.error
        : `${gb(p.done)} GB of ${gb(p.total)} GB`;

  return (
    <div className="flex max-w-2xl flex-col gap-4 rounded-lg bg-surface p-6">
      <div className="flex items-baseline justify-between gap-4">
        <span className="text-h3">{label}</span>
        {p.state !== "error" && <span className="tabular text-small text-ink-muted">{Math.floor(share * 100)}%</span>}
      </div>
      {p.state !== "error" && (
        <div className="h-2 overflow-hidden rounded-pill bg-ink/5" role="progressbar" aria-label={label} aria-valuenow={Math.floor(share * 100)} aria-valuemin={0} aria-valuemax={100}>
          <div className="h-full origin-left rounded-pill bg-brand transition-transform duration-500 ease-ui" style={{ transform: `scaleX(${share})` }} />
        </div>
      )}
      <p role="status" className={`text-small ${p.state === "error" ? "text-risk-high" : "text-ink-muted"}`}>
        {meta}
      </p>
      <div className="flex flex-wrap gap-2">
        {p.state === "downloading" && (
          <Button variant="secondary" onClick={onPause}>
            Pause
          </Button>
        )}
        {(p.state === "paused" || p.state === "error") && <Button onClick={onResume}>{p.state === "paused" ? "Resume" : "Try the download again"}</Button>}
        {p.state === "error" && (
          <Button variant="quiet" onClick={onReset}>
            Choose another way
          </Button>
        )}
      </div>
    </div>
  );
}

function Done({ name }: { name: string }) {
  return (
    <div className="flex max-w-2xl flex-col gap-5">
      <span className="inline-flex items-center gap-2 text-small text-ink-muted">
        <span aria-hidden className="size-2 rounded-pill bg-risk-low" />
        Installed and checked
      </span>
      <h1 className="text-h2 md:text-h1">You're set.</h1>
      <p className="text-lead text-ink-muted">{name} is installed and checked. From here on, FarmTwin works without internet.</p>
      <Link to="/" className="inline-flex min-h-11 items-center self-start rounded-pill bg-ink px-5 text-small text-on-ink hover:bg-ink/90">
        Add your first farm
      </Link>
    </div>
  );
}
