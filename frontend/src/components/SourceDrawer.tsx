import { useEffect } from "react";
import type { CitedChunk } from "../lib/api";

type Props = {
  chunk: CitedChunk | null;
  onClose: () => void;
};

export default function SourceDrawer({ chunk, onClose }: Props) {
  useEffect(() => {
    if (!chunk) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [chunk, onClose]);

  const open = chunk !== null;

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-ink/30 transition-opacity ${
          open ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
      />
      <aside
        className={`fixed top-0 right-0 z-50 h-full w-[440px] max-w-full bg-card border-l border-border shadow-xl transform transition-transform duration-200 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {chunk && (
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <div className="text-[11px] uppercase tracking-wide text-ink-faint">
                Source · {chunk.citation}
              </div>
              <button
                type="button"
                onClick={onClose}
                className="text-ink-faint hover:text-ink text-lg leading-none"
                aria-label="Close"
              >
                ×
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-5">
              <h3 className="text-lg font-semibold text-ink">
                {chunk.chunk_title}
              </h3>
              <div className="text-sm text-ink-muted mt-1">
                {chunk.source_title}
              </div>
              <div className="flex gap-2 mt-3 flex-wrap">
                {chunk.source_org && (
                  <span className="text-[11px] rounded-full bg-primary-tint text-primary px-2.5 py-1">
                    {chunk.source_org}
                  </span>
                )}
                {chunk.region && (
                  <span className="text-[11px] rounded-full bg-primary-tint text-primary px-2.5 py-1">
                    {chunk.region}
                  </span>
                )}
                {chunk.crop && (
                  <span className="text-[11px] rounded-full bg-primary-tint text-primary px-2.5 py-1">
                    {chunk.crop}
                  </span>
                )}
              </div>
              {chunk.topics && chunk.topics.length > 0 && (
                <div className="flex gap-1.5 mt-3 flex-wrap">
                  {chunk.topics.map((t) => (
                    <span
                      key={t}
                      className="text-[10px] rounded bg-bg text-ink-muted px-2 py-0.5"
                    >
                      #{t}
                    </span>
                  ))}
                </div>
              )}
              <hr className="border-border my-5" />
              <div className="text-sm text-ink whitespace-pre-wrap leading-relaxed">
                {chunk.content}
              </div>
              <p className="text-[11px] text-ink-faint mt-6 border-t border-border pt-3">
                This chunk is one of 45 in the local agricultural knowledge
                corpus. All retrieval is offline.
              </p>
            </div>
          </div>
        )}
      </aside>
    </>
  );
}
