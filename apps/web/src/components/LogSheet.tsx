import { useState } from "react";
import { createObservation, type FieldState, type Observation, type ObsType } from "../lib/api";
import Button from "./Button";
import Sheet from "./Sheet";

type Kind = { type: ObsType; label: string; unit?: string; placeholder: string; numeric: boolean };

const KINDS: Kind[] = [
  { type: "rainfall", label: "Rain", unit: "mm", placeholder: "How many mm?", numeric: true },
  { type: "pest", label: "Pests", placeholder: "What did you see, and where?", numeric: false },
  { type: "disease", label: "Disease", placeholder: "Spots, wilting, colour changes…", numeric: false },
  { type: "humidity", label: "Humidity", unit: "%", placeholder: "Relative humidity, %", numeric: true },
  { type: "temperature", label: "Heat", unit: "°C", placeholder: "Highest temperature, °C", numeric: true },
  { type: "note", label: "Note", placeholder: "Anything else worth remembering", numeric: false },
];

type LogSheetProps = {
  open: boolean;
  fields: FieldState[];
  /** preselects a field, e.g. when opened from a plot in the 3D view; pair it with a `key` */
  initialField?: number | null;
  onClose: () => void;
  onSaved: (obs: Observation, label: string) => void;
};

function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Log one reading against a field. Saving closes the sheet; the screen offers Undo. */
export default function LogSheet({ open, fields, initialField = null, onClose, onSaved }: LogSheetProps) {
  const [kind, setKind] = useState<Kind>(KINDS[0]);
  const [fieldId, setFieldId] = useState<number | null>(initialField);
  const [value, setValue] = useState("");
  const [day, setDay] = useState(today);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const field = fieldId ?? fields[0]?.id ?? null;

  const save = async () => {
    const text = value.trim();
    const number = Number(text.replace(",", "."));
    if (!text) return setError(kind.numeric ? "Enter a number." : "Write what you saw.");
    if (kind.numeric && (!Number.isFinite(number) || number < 0)) return setError("That needs to be a number, 0 or more.");
    if (field === null) return setError("Add a field to this farm first.");

    setSaving(true);
    setError(null);
    try {
      // a log for today keeps the current time; a past day is logged at 8am
      const at = day === today() ? new Date() : new Date(`${day}T08:00:00`);
      const obs = await createObservation({
        field_id: field,
        obs_type: kind.type,
        value_numeric: kind.numeric ? number : null,
        value_text: kind.numeric ? null : text,
        unit: kind.unit ?? null,
        observed_at: at.toISOString(),
      });
      setValue("");
      onSaved(obs, kind.label);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Sheet open={open} title="Log an observation" onClose={onClose}>
      <form
        className="flex flex-col gap-5"
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <div role="radiogroup" aria-label="What are you logging?" className="flex flex-wrap gap-2">
          {KINDS.map((k) => (
            <button
              key={k.type}
              type="button"
              role="radio"
              aria-checked={k.type === kind.type}
              onClick={() => {
                setKind(k);
                setError(null);
              }}
              className={`min-h-11 rounded-pill px-4 text-small transition duration-150 ease-ui ${
                k.type === kind.type ? "bg-brand-tint text-ink" : "bg-ink/5 text-ink-muted hover:text-ink"
              }`}
            >
              {k.label}
            </button>
          ))}
        </div>

        {fields.length > 1 && (
          <label className="flex flex-col gap-2 text-small text-ink-muted">
            Field
            <select
              value={field ?? ""}
              onChange={(e) => setFieldId(Number(e.target.value))}
              className="min-h-11 rounded-md bg-surface px-4 text-body text-ink ring-1 ring-hairline ring-inset"
            >
              {fields.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="flex flex-col gap-2 text-small text-ink-muted">
          {kind.label}
          {kind.numeric ? (
            <span className="flex items-center gap-2 rounded-md bg-surface px-4 ring-1 ring-hairline ring-inset">
              <input
                autoFocus
                inputMode="decimal"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder={kind.placeholder}
                className="min-h-11 flex-1 bg-transparent text-body text-ink outline-none placeholder:text-ink-muted"
              />
              <span className="text-ink-muted">{kind.unit}</span>
            </span>
          ) : (
            <textarea
              autoFocus
              rows={3}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={kind.placeholder}
              className="rounded-md bg-surface px-4 py-3 text-body text-ink ring-1 ring-hairline ring-inset outline-none placeholder:text-ink-muted"
            />
          )}
        </label>

        <label className="flex flex-col gap-2 text-small text-ink-muted">
          Day
          <input
            type="date"
            value={day}
            max={today()}
            onChange={(e) => setDay(e.target.value)}
            className="min-h-11 rounded-md bg-surface px-4 text-body text-ink ring-1 ring-hairline ring-inset"
          />
        </label>

        {error && <p className="text-small text-risk-high">{error}</p>}
        <div className="flex gap-2">
          <Button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save log"}
          </Button>
          <Button type="button" variant="quiet" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </form>
    </Sheet>
  );
}
