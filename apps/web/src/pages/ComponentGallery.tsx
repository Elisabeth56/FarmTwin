import { useState } from "react";
import Button from "../components/Button";
import Card from "../components/Card";
import CropChip from "../components/CropChip";
import FloatingSidebar from "../components/FloatingSidebar";
import Logo from "../components/Logo";
import RiskBadge from "../components/RiskBadge";
import Sheet from "../components/Sheet";
import { CROPS } from "../lib/crops";

/** Dev-only page (/_components) for checking the base components against the design system. */
export default function ComponentGallery() {
  const [selected, setSelected] = useState<string>("cowpea");
  const [sheet, setSheet] = useState(false);
  return (
    <div className="min-h-full md:pl-64">
      <FloatingSidebar
        items={[
          { to: "/_components", label: "Components", end: true },
          { to: "/", label: "Farms", end: true },
        ]}
        footer={<p className="px-2 text-caption text-ink-muted">Model running</p>}
      />
      <main className="mx-auto flex max-w-3xl flex-col gap-8 px-4 py-8">
        <h1 className="text-h2">Components</h1>
        <Card className="flex flex-wrap items-center gap-3">
          <Button>Ask FarmTwin</Button>
          <Button variant="secondary">Log rain</Button>
          <Button variant="quiet">Cancel</Button>
          <Button disabled>Downloading model · 42%</Button>
        </Card>
        <Card className="flex flex-wrap gap-2">
          {CROPS.map((crop) => (
            <CropChip key={crop} crop={crop} selected={crop === selected} onClick={() => setSelected(crop)} />
          ))}
        </Card>
        <Card className="flex flex-wrap gap-2">
          <RiskBadge name="Pests at flowering" level="high" />
          <RiskBadge name="Damp weather blast" level="medium" />
          <RiskBadge name="Dry spell" level="low" />
        </Card>
        <Card className="flex items-center justify-between">
          <Logo />
          <Button variant="secondary" onClick={() => setSheet(true)}>
            Open sheet
          </Button>
        </Card>
        <p className="text-small text-ink-muted">
          Body copy in ink-muted. <a className="text-brand underline" href="#">A link in brand.</a>
        </p>
      </main>
      <Sheet open={sheet} title="Log an observation" onClose={() => setSheet(false)}>
        <p className="mb-6 text-small text-ink-muted">Sheets rise from the bottom on phones and sit centred on wider screens.</p>
        <Button onClick={() => setSheet(false)}>Done</Button>
      </Sheet>
    </div>
  );
}
