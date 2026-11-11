import type { ReactNode } from "react";
import FloatingSidebar from "./FloatingSidebar";

const ITEMS = [{ to: "/", label: "Farms", end: true, also: ["/farm/", "/setup"] }];

/** Floating sidebar plus the page. Every in-app screen sits inside this. */
export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-full md:pl-64">
      <FloatingSidebar
        items={ITEMS}
        footer={
          <div className="rounded-md bg-surface p-3 text-caption text-ink-muted">
            Runs on this computer. Your farm data stays here.
          </div>
        }
      />
      <main className="mx-auto w-full max-w-6xl px-4 py-6 md:px-8 md:py-10">{children}</main>
    </div>
  );
}
