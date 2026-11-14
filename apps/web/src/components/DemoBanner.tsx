import { useEffect } from "react";

/** Top strip on the website demo: what's real here and what isn't. */
export default function DemoBanner() {
  // make room for the strip; the sidebar reads --shell-top
  useEffect(() => {
    const root = document.documentElement.style;
    root.setProperty("--shell-top", "3.5rem");
    root.paddingTop = "2.5rem";
  }, []);

  return (
    <div className="fixed inset-x-0 top-0 z-50 flex h-10 items-center justify-center gap-3 bg-ink px-4 text-small text-on-ink">
      <span className="truncate">
        <span className="sm:hidden">Demo · nothing you log is saved</span>
        <span className="hidden sm:inline">Demo: the sample farm in your browser. New logs stay in this tab and don't change the risk cards.</span>
      </span>
      <a href="/download/" className="shrink-0 rounded-pill bg-on-ink/15 px-3 py-0.5 hover:bg-on-ink/25">
        Download
      </a>
    </div>
  );
}
