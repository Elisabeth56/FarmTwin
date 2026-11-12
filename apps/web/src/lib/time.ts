/** "today", "yesterday", "3 days ago", "last week", or a date for anything older. */
export function loggedAgo(iso: string | null, now = new Date()): string {
  if (!iso) return "Nothing logged yet";
  const then = new Date(iso);
  const days = Math.floor((startOfDay(now) - startOfDay(then)) / 86_400_000);
  if (days <= 0) return "Logged today";
  if (days === 1) return "Logged yesterday";
  if (days < 7) return `Logged ${days} days ago`;
  if (days < 14) return "Logged last week";
  return `Logged ${then.toLocaleDateString(undefined, { day: "numeric", month: "short" })}`;
}

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}
