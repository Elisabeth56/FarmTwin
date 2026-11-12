const BASE_URL = "/api";

/** Reads the API's shared error shape and returns its plain message. */
export async function errorMessage(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { error?: { message?: string } };
    if (body.error?.message) return body.error.message;
  } catch {
    /* not json */
  }
  return "Something went wrong. Try again.";
}

export async function fetchAPI<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json() as Promise<T>;
}

export function getHealth(): Promise<{ status: string }> {
  return fetchAPI<{ status: string }>("/health");
}

// ---------- Types (mirror backend Pydantic Read schemas) ----------

export type Farm = {
  id: number;
  name: string;
  region: string | null;
  latitude: number | null;
  longitude: number | null;
  area_hectares: number | null;
  created_at: string;
};

export type FarmCreate = {
  name: string;
  region?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  area_hectares?: number | null;
};

export type Field = {
  id: number;
  farm_id: number;
  name: string;
  area_hectares: number | null;
  soil_type: string | null;
  soil_ph_estimate: number | null;
  notes: string | null;
};

export type FieldCreate = {
  farm_id: number;
  name: string;
  area_hectares?: number | null;
  soil_type?: string | null;
  soil_ph_estimate?: number | null;
  notes?: string | null;
};

export type Crop = {
  id: number;
  field_id: number;
  crop_type: string;
  variety: string | null;
  planting_date: string | null;
  status: string | null;
  created_at: string;
};

export type CropCreate = {
  field_id: number;
  crop_type: string;
  variety?: string | null;
  planting_date?: string | null;
  status?: string | null;
};

export type ObsType =
  | "rainfall"
  | "humidity"
  | "temperature"
  | "pest"
  | "disease"
  | "note";

export type Observation = {
  id: number;
  field_id: number;
  obs_type: string;
  value_numeric: number | null;
  value_text: string | null;
  unit: string | null;
  observed_at: string;
  created_at: string;
};

export type ObservationCreate = {
  field_id: number;
  obs_type: ObsType;
  value_numeric?: number | null;
  value_text?: string | null;
  unit?: string | null;
  observed_at: string;
};

export type WeatherSnapshot = {
  id: number;
  farm_id: number;
  snapshot_date: string;
  rainfall_mm: number | null;
  temp_min_c: number | null;
  temp_max_c: number | null;
  humidity_pct: number | null;
  notes: string | null;
};

export type WeatherCreate = {
  farm_id: number;
  snapshot_date: string;
  rainfall_mm?: number | null;
  temp_min_c?: number | null;
  temp_max_c?: number | null;
  humidity_pct?: number | null;
  notes?: string | null;
};

// ---------- Farms ----------

export function createFarm(data: FarmCreate): Promise<Farm> {
  return fetchAPI<Farm>("/farms", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getFarms(): Promise<Farm[]> {
  return fetchAPI<Farm[]>("/farms");
}

export type Risk = {
  id: string;
  title: string;
  severity: "high" | "medium" | "low";
  urgency: "immediate" | "this_week" | "monitor";
  reason: string;
  facts: string[];
  source: string;
  crop: string;
  field: string;
  planting_id: number;
};

export type FarmSummary = {
  id: number;
  name: string;
  region: string | null;
  area_hectares: number | null;
  plots: { planting_id: number; crop: string; field: string; share: number }[];
  risks: Risk[];
  last_logged_at: string | null;
};

export function getFarmSummaries(): Promise<FarmSummary[]> {
  return fetchAPI<FarmSummary[]>("/farms/summary");
}

export function createSampleFarm(): Promise<Farm> {
  return fetchAPI<Farm>("/farms/sample", { method: "POST" });
}

export function getFarm(id: number): Promise<Farm> {
  return fetchAPI<Farm>(`/farms/${id}`);
}

// ---------- Fields ----------

export function createField(data: FieldCreate): Promise<Field> {
  return fetchAPI<Field>("/fields", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getFields(farm_id?: number): Promise<Field[]> {
  const q = farm_id !== undefined ? `?farm_id=${farm_id}` : "";
  return fetchAPI<Field[]>(`/fields${q}`);
}

// ---------- Crops ----------

export function createCrop(data: CropCreate): Promise<Crop> {
  return fetchAPI<Crop>("/plantings", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getCrops(farm_id?: number): Promise<Crop[]> {
  const q = farm_id !== undefined ? `?farm_id=${farm_id}` : "";
  return fetchAPI<Crop[]>(`/plantings${q}`);
}

// ---------- Observations ----------

export function createObservation(
  data: ObservationCreate,
): Promise<Observation> {
  return fetchAPI<Observation>("/observations", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getObservations(farm_id?: number): Promise<Observation[]> {
  const q = farm_id !== undefined ? `?farm_id=${farm_id}` : "";
  return fetchAPI<Observation[]>(`/observations${q}`);
}

// ---------- Weather ----------

export function createWeatherSnapshot(
  data: WeatherCreate,
): Promise<WeatherSnapshot> {
  return fetchAPI<WeatherSnapshot>("/weather", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getWeather(farm_id?: number): Promise<WeatherSnapshot[]> {
  const q = farm_id !== undefined ? `?farm_id=${farm_id}` : "";
  return fetchAPI<WeatherSnapshot[]>(`/weather${q}`);
}

// ---------- Ask ----------

export type AskRequest = {
  farm_id: number;
  question: string;
};

export type Priority = "high" | "medium" | "low";

export type Recommendation = {
  what: string;
  why: string;
  when_urgency: string;
  risk_if_ignored: string;
  priority: Priority;
};

export type CitedChunk = {
  citation: string;
  chunk_id: number;
  source_org: string;
  source_title: string;
  chunk_title: string;
  content: string;
  region: string;
  crop: string;
  topics: string[];
  distance: number;
};

export type AskResponse = {
  narrative: string;
  recommendations: Recommendation[];
  cited_chunks: CitedChunk[];
  model_name: string;
  timing_ms: {
    prompt_ms?: number;
    generation_ms?: number;
    llm_wallclock_ms?: number;
    total_ms: number;
  };
  saved_recommendation_ids: number[];
};

export type AnswerKind = "answer" | "not_in_sources" | "no_planting";

export type StreamEvent =
  | { type: "progress"; message: string }
  | { type: "ready"; cited_chunks: CitedChunk[] }
  | { type: "token"; content: string }
  | {
      type: "recommendation_ready";
      kind: AnswerKind;
      narrative: string;
      recommendations: Recommendation[];
      cited_chunks?: CitedChunk[];
      saved_recommendation_ids: number[];
      model_name: string;
      timing_ms: {
        prompt_ms?: number;
        generation_ms?: number;
        llm_wallclock_ms?: number;
        total_ms: number;
      };
    }
  | { type: "error"; message: string; code?: string };

export async function askQuestionStream(
  req: AskRequest,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") return;
    const message = err instanceof Error ? err.message : "Network error";
    onEvent({ type: "error", message });
    return;
  }

  if (!res.ok) {
    if (res.status === 503) {
      onEvent({ type: "error", message: await errorMessage(res) });
      return;
    }
    onEvent({ type: "error", message: await errorMessage(res) });
    return;
  }

  if (!res.body) {
    onEvent({ type: "error", message: "No response body from server." });
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sepIdx: number;
      while ((sepIdx = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, sepIdx);
        buffer = buffer.slice(sepIdx + 2);
        // An SSE event can have multiple `data:` lines; concatenate their payloads.
        const dataLines: string[] = [];
        for (const line of rawEvent.split("\n")) {
          const trimmed = line.trimStart();
          if (trimmed.startsWith("data:")) {
            dataLines.push(trimmed.slice(5).trimStart());
          }
        }
        if (dataLines.length === 0) continue;
        const payload = dataLines.join("\n");
        try {
          const parsed = JSON.parse(payload) as StreamEvent;
          onEvent(parsed);
        } catch {
          // Skip malformed events but keep the stream alive.
        }
      }
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") return;
    const message = err instanceof Error ? err.message : "Stream read error";
    onEvent({ type: "error", message });
  } finally {
    try {
      reader.releaseLock();
    } catch {
      /* ignore */
    }
  }
}

// ---------- Transcribe ----------

export type TranscribeResponse = {
  text: string;
  language_requested: string;
  language_used: string;
  duration_ms: number;
};

export async function transcribeAudio(
  audioBlob: Blob,
  language: "en" = "en",
): Promise<TranscribeResponse> {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");
  formData.append("language", language);
  const response = await fetch(`${BASE_URL}/transcribe`, {
    method: "POST",
    body: formData,
    signal: AbortSignal.timeout(90000),
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return (await response.json()) as TranscribeResponse;
}

export async function askQuestion(req: AskRequest): Promise<AskResponse> {
  try {
    const res = await fetch(`${BASE_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
      signal: AbortSignal.timeout(300000),
    });
    if (!res.ok) {
      throw new Error(await errorMessage(res));
    }
    return (await res.json()) as AskResponse;
  } catch (err) {
    if (err instanceof Error) {
      if (
        err.name === "TimeoutError" ||
        err.name === "AbortError" ||
        /timeout/i.test(err.message)
      ) {
        throw new Error(
          "Model took too long to respond — try again or check system load.",
        );
      }
      throw err;
    }
    throw new Error("Ask failed: unknown error");
  }
}

// ---------- Farm screen ----------

export type PlantingProgress = {
  id: number;
  crop: string;
  variety: string | null;
  stage: string;
  day: number | null;
  cycle_days: number;
  progress: number | null;
  harvest_start: string | null;
  harvest_end: string | null;
};

export type FieldState = {
  id: number;
  name: string;
  area_hectares: number | null;
  soil_type: string | null;
  plantings: PlantingProgress[];
};

export type LogEntry = {
  id: number;
  field: string;
  obs_type: ObsType;
  value_numeric: number | null;
  value_text: string | null;
  unit: string | null;
  observed_at: string;
};

export type FarmDashboardData = {
  farm: Farm;
  fields: FieldState[];
  rainfall: { day: string; mm: number | null }[];
  risks: Risk[];
  recent_logs: LogEntry[];
};

export function getFarmDashboard(id: number): Promise<FarmDashboardData> {
  return fetchAPI<FarmDashboardData>(`/farms/${id}/dashboard`);
}

export async function deleteObservation(id: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/observations/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await errorMessage(res));
}

// ---------- Local model ----------

export type ModelStatus = {
  state: "ready" | "starting" | "stopped" | "not_set_up";
  managed: boolean;
  detail: string;
};

export function getModelStatus(): Promise<ModelStatus> {
  return fetchAPI<ModelStatus>("/model/status");
}

export function restartModel(): Promise<ModelStatus> {
  return fetchAPI<ModelStatus>("/model/restart", { method: "POST" });
}
