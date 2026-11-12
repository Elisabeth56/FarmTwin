# ADR-028: The 3D farm lives in `packages/twin`

- Status: Accepted
- Date: 2026-11-12
- Amends: ADR-026 (repo layout)

## Context
The 3D farm started on the website's landing page (`apps/site/src/scripts/twin.js`). The farm screen in the app (#24) needs the same scene, drawn with the farm's own plantings. Two copies of a 400-line Three.js scene would drift.

## Options
- **Copy the file into `apps/web`.** No layout change; two copies to keep in step.
- **Import across apps** (`apps/web` importing from `apps/site/src`). One copy, but the app's build would depend on the website's source tree.
- **A small workspace package.** One copy, imported by name by both apps.

## Decision
Move the module to `packages/twin` (`@farmtwin/twin`), a plain ES module with a hand-written `.d.ts`, no build step. `three` is its only dependency. `packages/*` is added to the pnpm workspace; this is the only package for now.

## Consequences
- The site and the app draw the same farm. The scene takes `plots`, `badgePlot` and `onDemand` options; the landing page keeps its defaults.
- In the app the scene renders only while something moves (entrance, drag, hover, rain), and `dispose()` frees the GPU objects when the farm screen unmounts.
- Changes to the scene can affect both apps; CI builds both.
