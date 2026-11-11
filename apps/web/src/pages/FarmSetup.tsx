import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import Button from "../components/Button";
import Card from "../components/Card";
import FieldLabel from "../components/FieldLabel";
import Input from "../components/Input";
import Select from "../components/Select";
import { createCrop, createFarm, createField } from "../lib/api";

function daysAgoISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

const SOIL_TYPES = [
  "sandy loam",
  "clay loam",
  "sandy",
  "clay",
  "loam",
  "other",
];

const CROP_TYPES = ["maize", "rice", "cassava", "yam"];

export default function FarmSetup() {
  const navigate = useNavigate();
  const defaultPlantingDate = useMemo(() => daysAgoISO(45), []);

  const [farmName, setFarmName] = useState("");
  const [region, setRegion] = useState("Kaduna");
  const [farmArea, setFarmArea] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");

  const [fieldName, setFieldName] = useState("Main Field");
  const [soilType, setSoilType] = useState("sandy loam");
  const [fieldArea, setFieldArea] = useState("");

  const [cropType, setCropType] = useState("maize");
  const [variety, setVariety] = useState("");
  const [plantingDate, setPlantingDate] = useState(defaultPlantingDate);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requiredOk =
    farmName.trim() !== "" &&
    region.trim() !== "" &&
    farmArea.trim() !== "" &&
    fieldName.trim() !== "" &&
    soilType.trim() !== "" &&
    cropType.trim() !== "" &&
    plantingDate.trim() !== "";

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!requiredOk || submitting) return;
    setError(null);
    setSubmitting(true);
    try {
      const farmAreaNum = Number(farmArea);
      const farm = await createFarm({
        name: farmName.trim(),
        region: region.trim(),
        area_hectares: Number.isFinite(farmAreaNum) ? farmAreaNum : null,
        latitude: latitude.trim() !== "" ? Number(latitude) : null,
        longitude: longitude.trim() !== "" ? Number(longitude) : null,
      });

      const fieldAreaNum = fieldArea.trim() !== "" ? Number(fieldArea) : farmAreaNum;
      const field = await createField({
        farm_id: farm.id,
        name: fieldName.trim(),
        soil_type: soilType,
        area_hectares: Number.isFinite(fieldAreaNum) ? fieldAreaNum : null,
      });

      await createCrop({
        field_id: field.id,
        crop_type: cropType,
        variety: variety.trim() !== "" ? variety.trim() : null,
        planting_date: plantingDate,
        status: "active",
      });

      navigate(`/farm/${farm.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen">
      <header className="px-6 py-5 max-w-6xl mx-auto w-full flex items-center gap-6">
        <Link to="/" className="text-lg font-semibold text-primary">
          🌱 FarmTwin
        </Link>
        <Link
          to="/"
          className="text-sm text-ink-muted hover:text-ink transition-colors"
        >
          ← Back
        </Link>
      </header>

      <main className="px-6 pb-16">
        <div className="max-w-[560px] mx-auto pt-6">
          <h1 className="text-3xl font-semibold tracking-tight">
            Create your farm
          </h1>
          <p className="text-ink-muted mt-2">
            Tell us about your farm so FarmTwin can advise you specifically.
          </p>

          <form onSubmit={handleSubmit} className="mt-8">
            <Card>
              {/* Farm section */}
              <div>
                <div className="text-xs uppercase tracking-wide text-ink-faint">
                  Farm
                </div>
                <div className="mt-4 space-y-4">
                  <div>
                    <FieldLabel htmlFor="farmName" required>
                      Farm name
                    </FieldLabel>
                    <Input
                      id="farmName"
                      value={farmName}
                      onChange={(e) => setFarmName(e.target.value)}
                      placeholder="e.g. Adamu Farm"
                      required
                    />
                  </div>
                  <div>
                    <FieldLabel htmlFor="region" required>
                      Region
                    </FieldLabel>
                    <Input
                      id="region"
                      value={region}
                      onChange={(e) => setRegion(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <FieldLabel htmlFor="farmArea" required>
                      Area (hectares)
                    </FieldLabel>
                    <Input
                      id="farmArea"
                      type="number"
                      step="0.1"
                      min="0"
                      value={farmArea}
                      onChange={(e) => setFarmArea(e.target.value)}
                      placeholder="e.g. 2.5"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <FieldLabel htmlFor="latitude">Latitude</FieldLabel>
                      <Input
                        id="latitude"
                        type="number"
                        step="0.01"
                        value={latitude}
                        onChange={(e) => setLatitude(e.target.value)}
                        placeholder="10.5"
                      />
                    </div>
                    <div>
                      <FieldLabel htmlFor="longitude">Longitude</FieldLabel>
                      <Input
                        id="longitude"
                        type="number"
                        step="0.01"
                        value={longitude}
                        onChange={(e) => setLongitude(e.target.value)}
                        placeholder="7.4"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Field section */}
              <div className="mt-8">
                <div className="text-xs uppercase tracking-wide text-ink-faint">
                  Field
                </div>
                <div className="mt-4 space-y-4">
                  <div>
                    <FieldLabel htmlFor="fieldName" required>
                      Field name
                    </FieldLabel>
                    <Input
                      id="fieldName"
                      value={fieldName}
                      onChange={(e) => setFieldName(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <FieldLabel htmlFor="soilType" required>
                      Soil type
                    </FieldLabel>
                    <Select
                      id="soilType"
                      value={soilType}
                      onChange={(e) => setSoilType(e.target.value)}
                      required
                    >
                      {SOIL_TYPES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </Select>
                  </div>
                  <div>
                    <FieldLabel htmlFor="fieldArea">
                      Field area (hectares)
                    </FieldLabel>
                    <Input
                      id="fieldArea"
                      type="number"
                      step="0.1"
                      min="0"
                      value={fieldArea}
                      onChange={(e) => setFieldArea(e.target.value)}
                      placeholder="Defaults to farm area"
                    />
                  </div>
                </div>
              </div>

              {/* Crop section */}
              <div className="mt-8">
                <div className="text-xs uppercase tracking-wide text-ink-faint">
                  Crop
                </div>
                <div className="mt-4 space-y-4">
                  <div>
                    <FieldLabel htmlFor="cropType" required>
                      Crop type
                    </FieldLabel>
                    <Select
                      id="cropType"
                      value={cropType}
                      onChange={(e) => setCropType(e.target.value)}
                      required
                    >
                      {CROP_TYPES.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </Select>
                  </div>
                  <div>
                    <FieldLabel htmlFor="variety">Variety</FieldLabel>
                    <Input
                      id="variety"
                      value={variety}
                      onChange={(e) => setVariety(e.target.value)}
                      placeholder="SAMMAZ 15"
                    />
                  </div>
                  <div>
                    <FieldLabel htmlFor="plantingDate" required>
                      Planting date
                    </FieldLabel>
                    <Input
                      id="plantingDate"
                      type="date"
                      value={plantingDate}
                      onChange={(e) => setPlantingDate(e.target.value)}
                      required
                    />
                  </div>
                </div>
              </div>

              {error && (
                <div className="mt-6 rounded-xl border border-risk-high/40 bg-risk-high/5 text-risk-high text-sm px-4 py-3">
                  {error}
                </div>
              )}

              <div className="mt-8">
                <Button
                  type="submit"
                  disabled={!requiredOk || submitting}
                  className="w-full"
                >
                  {submitting ? "Creating..." : "Create farm & continue"}
                </Button>
              </div>
            </Card>
          </form>
        </div>
      </main>
    </div>
  );
}
