/** "root_initiation" → "root initiation" */
export function stageLabel(stage: string): string {
  if (stage === "unknown") return "no calendar yet";
  return stage.replaceAll("_", " ");
}

export function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

/** Harvest timing in words, from today to the expected window. */
export function harvestLine(start: string | null, end: string | null, today = new Date()): string | null {
  if (!start || !end) return null;
  const days = Math.round((new Date(start).getTime() - today.getTime()) / 86_400_000);
  if (days > 13) return `Harvest window opens in about ${Math.round(days / 7)} weeks.`;
  if (days > 1) return `Harvest window opens in ${days} days.`;
  if (new Date(end).getTime() >= today.getTime()) return `Harvest window is open until ${shortDate(end)}.`;
  return "Past the expected harvest window.";
}
