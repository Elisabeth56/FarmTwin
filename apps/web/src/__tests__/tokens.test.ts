import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const SRC = join(__dirname, "..");
const css = readFileSync(join(SRC, "index.css"), "utf8");

function tokens(block: string): Record<string, string> {
  return Object.fromEntries([...block.matchAll(/--([a-z-]+):\s*(#[0-9a-f]{6});/g)].map((m) => [m[1], m[2]]));
}

const light = tokens(css.slice(css.indexOf(":root"), css.indexOf("@media (prefers-color-scheme")));
const dark = { ...light, ...tokens(css.slice(css.indexOf("@media (prefers-color-scheme"), css.indexOf("@theme"))) };

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// [foreground, background, minimum ratio]: 4.5 for text, 3 for focus rings, dots and large numerals
const PAIRS: [string, string, number][] = [
  ["ink", "ground", 4.5],
  ["ink", "surface", 4.5],
  ["ink", "raised", 4.5],
  ["ink-muted", "ground", 4.5],
  ["ink-muted", "surface", 4.5],
  ["on-ink", "ink", 4.5],
  ["ink", "brand-tint", 4.5],
  ["brand", "ground", 4.5],
  ["brand", "raised", 3],
  ["ink-faint", "ground", 3],
  // risk-high is also used for text in alerts; the other risk colours only for dots next to the level word
  ["risk-high", "ground", 4.5],
  ["risk-high", "surface", 4.5],
  ["risk-medium", "ground", 3],
  ["risk-low", "ground", 3],
];

describe.each([
  ["light", light],
  ["dark", dark],
])("%s theme contrast", (_, theme) => {
  it.each(PAIRS)("%s on %s is at least %s:1", (fg, bg, min) => {
    expect(contrast(theme[fg], theme[bg])).toBeGreaterThanOrEqual(min);
  });
});

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
}

it("colours come from tokens: no hex values outside index.css", () => {
  const offenders = files(SRC)
    .filter((f) => /\.(tsx?|css)$/.test(f) && !f.endsWith("index.css") && !f.includes("__tests__"))
    .filter((f) => /#[0-9a-fA-F]{3,8}\b/.test(readFileSync(f, "utf8")));
  expect(offenders).toEqual([]);
});
