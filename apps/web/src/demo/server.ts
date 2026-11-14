// The website demo: answers the app's /api calls in the browser from data the real API recorded
// (apps/api/scripts/record_demo.py). Only demo builds load this file (main.tsx, VITE_DEMO).

import type { FarmDashboardData, LogEntry, ObservationCreate, StreamEvent } from "../lib/api";
import fixtures from "./fixtures.json";

type Recorded = { after_ms: number; event: StreamEvent };

const DAY = 86_400_000;
const NOT_IN_DEMO = "That's part of the desktop app. Download FarmTwin to set up your own farms.";

/** Moves every date in the recording forward to today, so "2 days ago" stays true. */
function shiftDates<T>(value: T, days: number): T {
  const json = JSON.stringify(value).replace(/"(\d{4}-\d{2}-\d{2})(T[\d:.]+(?:Z|[+-]\d{2}:\d{2})?)?"/g, (_, date: string, time = "") => {
    const shifted = new Date(Date.parse(`${date}T00:00:00Z`) + days * DAY).toISOString().slice(0, 10);
    return `"${shifted}${time}"`;
  });
  return JSON.parse(json) as T;
}

const days = Math.round((Date.now() - Date.parse(fixtures.recorded_at)) / DAY);
const data = shiftDates(fixtures, days);
const dashboard = data.dashboard as FarmDashboardData;
let nextId = 1000;

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function error(status: number, code: string, message: string): Response {
  return json({ error: { code, message } }, status);
}

/** Logs are kept in this tab. Rainfall is a sum, so the chart follows; risks come from the
 * Python rules engine, which the demo doesn't run, so they stay as recorded. */
function addLog(body: ObservationCreate): Response {
  const field = dashboard.fields.find((f) => f.id === body.field_id);
  const entry: LogEntry = {
    id: nextId++,
    field: field?.name ?? "Field",
    obs_type: body.obs_type,
    value_numeric: body.value_numeric ?? null,
    value_text: body.value_text ?? null,
    unit: body.unit ?? null,
    observed_at: body.observed_at,
  };
  dashboard.recent_logs.unshift(entry);
  if (body.obs_type === "rainfall" && body.value_numeric != null) {
    const day = dashboard.rainfall.find((d) => d.day === body.observed_at.slice(0, 10));
    if (day) day.mm = (day.mm ?? 0) + body.value_numeric;
  }
  return json({ ...entry, field_id: body.field_id, created_at: new Date().toISOString() }, 201);
}

function removeLog(id: number): Response {
  const i = dashboard.recent_logs.findIndex((l) => l.id === id);
  if (i === -1) return error(404, "observation_not_found", "That log no longer exists.");
  const [log] = dashboard.recent_logs.splice(i, 1);
  if (log.obs_type === "rainfall" && log.value_numeric != null) {
    const day = dashboard.rainfall.find((d) => d.day === log.observed_at.slice(0, 10));
    if (day?.mm != null) day.mm = Math.max(0, day.mm - log.value_numeric) || null;
  }
  return new Response(null, { status: 204 });
}

/** Replays a recorded answer at the pace the real model produced it. */
function replay(events: Recorded[], signal?: AbortSignal | null): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      for (const { after_ms, event } of events) {
        await new Promise((r) => setTimeout(r, Math.min(after_ms, 1500)));
        if (signal?.aborted) return controller.close();
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
      }
      controller.close();
    },
  });
  return new Response(stream, { headers: { "Content-Type": "text/event-stream" } });
}

function ask(body: { question: string }, signal?: AbortSignal | null): Response {
  const answers = data.answers as Record<string, Recorded[]>;
  const key = Object.keys(answers).find((q) => q.toLowerCase() === body.question.trim().toLowerCase());
  if (key) return replay(answers[key], signal);
  const suggested = Object.keys(answers);
  const message = suggested.length
    ? `The demo replays real answers to the suggested questions only. Try "${suggested[0]}", or download FarmTwin to ask your own.`
    : "Questions run on the AI model on your laptop. Download FarmTwin to ask about your own farm.";
  return error(409, "demo_question", message);
}

async function route(method: string, path: string, body: unknown, signal?: AbortSignal | null): Promise<Response> {
  const id = data.farm.id;
  if (method === "GET") {
    if (path === "/health") return json({ status: "ok" });
    if (path === "/farms") return json(data.farms);
    if (path === "/farms/summary") return json(data.summaries);
    if (path === `/farms/${id}`) return json(data.farm);
    if (path === `/farms/${id}/dashboard`) return json(dashboard);
    if (path === "/model/status") return json({ state: "ready", managed: false, detail: "demo" });
    if (path === "/voice/status") return json({ ready: false, reason: null, needs_model: false });
  }
  if (method === "POST") {
    if (path === "/farms/sample") return json(data.farm, 201);
    if (path === "/observations") return addLog(body as ObservationCreate);
    if (path === "/ask/stream") return ask(body as { question: string }, signal);
  }
  if (method === "DELETE" && path.startsWith("/observations/")) return removeLog(Number(path.split("/").pop()));
  return error(404, "not_in_demo", NOT_IN_DEMO);
}

/** Routes the app's /api requests to the demo; everything else goes to the network as usual. */
export function startDemo(): void {
  const real = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const url = new URL(input instanceof Request ? input.url : String(input), window.location.href);
    if (url.origin !== window.location.origin || !url.pathname.startsWith("/api/")) return real(input, init);
    const method = (init?.method ?? "GET").toUpperCase();
    const body = typeof init?.body === "string" ? (JSON.parse(init.body) as unknown) : null;
    return route(method, url.pathname.slice(4), body, init?.signal);
  };
}
