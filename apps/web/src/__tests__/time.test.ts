import { expect, it } from "vitest";
import { loggedAgo } from "../lib/time";

const now = new Date(2026, 10, 12, 9, 0);

it.each([
  [null, "Nothing logged yet"],
  [new Date(2026, 10, 12, 7, 0).toISOString(), "Logged today"],
  [new Date(2026, 10, 11, 23, 0).toISOString(), "Logged yesterday"],
  [new Date(2026, 10, 9, 8, 0).toISOString(), "Logged 3 days ago"],
  [new Date(2026, 10, 2, 8, 0).toISOString(), "Logged last week"],
])("%s → %s", (iso, label) => {
  expect(loggedAgo(iso, now)).toBe(label);
});
