const BASE_URL = "/api";

export async function fetchAPI<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.text();
      detail = body ? ` — ${body}` : "";
    } catch {
      /* ignore */
    }
    throw new Error(`API ${path} failed: ${res.status} ${res.statusText}${detail}`);
  }
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
  return fetchAPI<Crop>("/crops", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getCrops(farm_id?: number): Promise<Crop[]> {
  const q = farm_id !== undefined ? `?farm_id=${farm_id}` : "";
  return fetchAPI<Crop[]>(`/crops${q}`);
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

export async function askQuestion(req: AskRequest): Promise<AskResponse> {
  try {
    const res = await fetch(`${BASE_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
      signal: AbortSignal.timeout(300000),
    });
    if (!res.ok) {
      if (res.status === 503) {
        throw new Error(
          "Local model not available. Start llama-server first.",
        );
      }
      let detail = "";
      try {
        const body = await res.text();
        detail = body ? ` — ${body}` : "";
      } catch {
        /* ignore */
      }
      throw new Error(
        `Ask failed: ${res.status} ${res.statusText}${detail}`,
      );
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
