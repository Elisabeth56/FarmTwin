# ADR-026: Astro + Starlight website; pnpm workspace layout

- Status: Accepted
- Date: 2026-11-11

## Context
FarmTwin needs a public site: landing page, docs (install, first run, troubleshooting), and a download page. Visitors are often on mobile data. The repo also has to hold the app UI, backend, desktop shell, site, knowledge, and evals.

## Options (site)
- **Next.js + a docs library.** The default stack; more JavaScript than a mostly static site needs.
- **Astro + Starlight.** Static by default, ships no JavaScript unless a component needs it, docs built in.

## Decision
- Site: Astro with Starlight for docs, deployed on Vercel. The download page reads the latest GitHub Release at build time and on the client, and highlights the visitor's OS.
- App UI stays Vite + React + TypeScript (Tauri needs a static build; Next.js adds nothing here). Tailwind v4.
- Layout (pnpm workspaces, uv for Python):

```
apps/web        Vite + React app UI
apps/api        FastAPI backend
apps/desktop    Tauri shell (src-tauri)
apps/site       Astro + Starlight
knowledge/      corpus/ and crops/
evals/          cases, runners, results
docs/           architecture.md, decisions/
```

## Consequences
- Two frontend frameworks in one repo. They share design tokens through one CSS file, not components.
- v1 ADRs (001–012) move from DECISIONS.md into `docs/decisions/` unchanged.
