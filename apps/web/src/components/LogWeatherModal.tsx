import { useEffect, useState } from "react";
import Button from "./Button";
import FieldLabel from "./FieldLabel";
import Input from "./Input";
import { createWeatherSnapshot } from "../lib/api";

export type LogWeatherModalProps = {
  isOpen: boolean;
  farmId: number;
  onClose: () => void;
  onSuccess: () => void;
};

function todayISO(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function toOptionalNumber(s: string): number | null {
  if (!s.trim()) return null;
  const n = Number(s);
  if (Number.isNaN(n)) throw new Error("Numeric fields must be numbers.");
  return n;
}

export default function LogWeatherModal({
  isOpen,
  farmId,
  onClose,
  onSuccess,
}: LogWeatherModalProps) {
  const [snapshotDate, setSnapshotDate] = useState(todayISO());
  const [rainfall, setRainfall] = useState("");
  const [humidity, setHumidity] = useState("");
  const [tempMin, setTempMin] = useState("");
  const [tempMax, setTempMax] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setSnapshotDate(todayISO());
      setRainfall("");
      setHumidity("");
      setTempMin("");
      setTempMax("");
      setNotes("");
      setError(null);
      setSubmitting(false);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const humidityNum = toOptionalNumber(humidity);
      if (humidityNum !== null && (humidityNum < 0 || humidityNum > 100)) {
        throw new Error("Humidity must be between 0 and 100.");
      }
      await createWeatherSnapshot({
        farm_id: farmId,
        snapshot_date: snapshotDate,
        rainfall_mm: toOptionalNumber(rainfall),
        humidity_pct: humidityNum,
        temp_min_c: toOptionalNumber(tempMin),
        temp_max_c: toOptionalNumber(tempMax),
        notes: notes.trim() || null,
      });
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to log weather.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-40 bg-ink/40 flex items-center justify-center"
      onClick={onClose}
    >
      <div
        className="bg-card max-w-md w-full mx-4 rounded-2xl p-6 shadow-xl border border-border relative"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 text-ink-faint hover:text-ink text-lg leading-none"
          aria-label="Close"
        >
          ×
        </button>
        <h2 className="text-xl font-semibold text-ink">Log a weather snapshot</h2>
        <p className="text-sm text-ink-muted mt-1">
          Record what the sky and thermometer showed today.
        </p>

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <FieldLabel required>Date</FieldLabel>
            <Input
              type="date"
              value={snapshotDate}
              onChange={(e) => setSnapshotDate(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <FieldLabel>Rainfall (mm)</FieldLabel>
              <Input
                type="number"
                step="any"
                value={rainfall}
                onChange={(e) => setRainfall(e.target.value)}
                placeholder="e.g. 12"
              />
            </div>
            <div>
              <FieldLabel>Humidity (%)</FieldLabel>
              <Input
                type="number"
                step="any"
                min={0}
                max={100}
                value={humidity}
                onChange={(e) => setHumidity(e.target.value)}
                placeholder="e.g. 75"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <FieldLabel>Min temp (°C)</FieldLabel>
              <Input
                type="number"
                step="any"
                value={tempMin}
                onChange={(e) => setTempMin(e.target.value)}
              />
            </div>
            <div>
              <FieldLabel>Max temp (°C)</FieldLabel>
              <Input
                type="number"
                step="any"
                value={tempMax}
                onChange={(e) => setTempMax(e.target.value)}
              />
            </div>
          </div>

          <div>
            <FieldLabel>Notes</FieldLabel>
            <textarea
              className="w-full rounded-xl border border-border bg-white px-4 py-2.5 text-ink placeholder:text-ink-faint focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors min-h-[70px]"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Anything unusual (optional)"
            />
          </div>

          {error && (
            <div className="text-sm text-risk-high bg-risk-high/10 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Logging…" : "Log weather"}
          </Button>
        </form>
      </div>
    </div>
  );
}
