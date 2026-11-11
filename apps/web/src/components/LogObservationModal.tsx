import { useEffect, useMemo, useState } from "react";
import Button from "./Button";
import FieldLabel from "./FieldLabel";
import Input from "./Input";
import Select from "./Select";
import { createObservation, type ObsType } from "../lib/api";

export type LogObservationModalProps = {
  isOpen: boolean;
  fieldId: number;
  onClose: () => void;
  onSuccess: () => void;
};

const OBS_TYPES: { value: ObsType; label: string }[] = [
  { value: "rainfall", label: "Rainfall" },
  { value: "humidity", label: "Humidity" },
  { value: "temperature", label: "Temperature" },
  { value: "pest", label: "Pest" },
  { value: "disease", label: "Disease" },
  { value: "note", label: "Note" },
];

const NUMERIC_TYPES: ObsType[] = ["rainfall", "humidity", "temperature"];

function defaultUnit(t: ObsType): string {
  switch (t) {
    case "rainfall":
      return "mm";
    case "humidity":
      return "percent";
    case "temperature":
      return "°C";
    default:
      return "";
  }
}

function placeholderFor(t: ObsType): string {
  switch (t) {
    case "rainfall":
      return "mm for last 24h";
    case "humidity":
      return "% relative humidity";
    case "temperature":
      return "°C";
    case "pest":
      return "e.g. fall armyworm larvae in whorls";
    case "disease":
      return "e.g. leaf lesions on lower leaves";
    default:
      return "free text";
  }
}

function todayISO(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export default function LogObservationModal({
  isOpen,
  fieldId,
  onClose,
  onSuccess,
}: LogObservationModalProps) {
  const [obsType, setObsType] = useState<ObsType>("rainfall");
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState(defaultUnit("rainfall"));
  const [obsDate, setObsDate] = useState(todayISO());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isNumeric = useMemo(() => NUMERIC_TYPES.includes(obsType), [obsType]);

  useEffect(() => {
    if (isOpen) {
      setObsType("rainfall");
      setValue("");
      setUnit(defaultUnit("rainfall"));
      setObsDate(todayISO());
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

  function handleTypeChange(next: ObsType) {
    setObsType(next);
    setValue("");
    setUnit(defaultUnit(next));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!value.trim()) {
      setError("Please enter a value.");
      return;
    }
    setSubmitting(true);
    try {
      const observedAt = new Date(`${obsDate}T12:00:00`).toISOString();
      const payload = {
        field_id: fieldId,
        obs_type: obsType,
        unit: unit || null,
        observed_at: observedAt,
        value_numeric: isNumeric ? Number(value) : null,
        value_text: isNumeric ? null : value,
      };
      if (isNumeric && Number.isNaN(payload.value_numeric)) {
        throw new Error("Value must be a number.");
      }
      await createObservation(payload);
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to log observation.");
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
        className="bg-surface max-w-md w-full mx-4 rounded-lg p-6 shadow-float border border-hairline relative"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 text-ink-faint hover:text-ink text-lead leading-none"
          aria-label="Close"
        >
          ×
        </button>
        <h2 className="text-h3 font-semibold text-ink">Log an observation</h2>
        <p className="text-small text-ink-muted mt-1">
          Tell FarmTwin what you're seeing on the farm.
        </p>

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <FieldLabel required>Type</FieldLabel>
            <Select
              value={obsType}
              onChange={(e) => handleTypeChange(e.target.value as ObsType)}
            >
              {OBS_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <FieldLabel required>Value</FieldLabel>
            <Input
              type={isNumeric ? "number" : "text"}
              step={isNumeric ? "any" : undefined}
              placeholder={placeholderFor(obsType)}
              value={value}
              onChange={(e) => setValue(e.target.value)}
            />
          </div>

          <div>
            <FieldLabel>Unit</FieldLabel>
            <Input
              type="text"
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              disabled={!isNumeric && obsType === "note"}
              placeholder={isNumeric ? "" : "optional"}
            />
          </div>

          <div>
            <FieldLabel required>Date</FieldLabel>
            <Input
              type="date"
              value={obsDate}
              onChange={(e) => setObsDate(e.target.value)}
            />
          </div>

          {error && (
            <div className="text-small text-risk-high bg-risk-high/10 rounded-sm px-3 py-2">
              {error}
            </div>
          )}

          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Logging…" : "Log observation"}
          </Button>
        </form>
      </div>
    </div>
  );
}
