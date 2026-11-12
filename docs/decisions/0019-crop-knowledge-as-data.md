# ADR-019: Crop calendars and risk rules as data; many plantings per field

- Status: Accepted
- Date: 2026-11-11

## Context
v2 covers maize, cassava, yam, sorghum, rice and cowpea, the most planted staples and the legume in common double-cropping systems. v1 hardcoded maize stages and rules in Python and allowed one active crop per field. Intercropping is common in Nigeria (cereals with legumes in the North, maize with root and tuber crops in the South).

## Options
- **Hardcoded Python per crop.** Simple for one crop; six crops means six code paths, and none of it ports to mobile.
- **One data file per crop, read by a small engine.** Stages and rules are data; the engine evaluates them.

## Decision
One file per crop in `knowledge/crops/<crop>.yaml` holding growth stages (by days after planting) and risk rules (conditions on observations and weather, severity, reason). A small engine computes stage and evaluates rules. The `crops` table becomes `plantings`, with many active plantings per field.

## Consequences
- Adding a crop means adding a file and its corpus documents.
- The rule format must stay small: comparisons over recent observations within a time window. Anything more complex goes back to code, with a test.
- A future mobile port reuses the YAML files and rewrites only the small engine.
