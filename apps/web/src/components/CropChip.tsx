import { cropColor, cropLabel } from "../lib/crops";

type CropChipProps = {
  crop: string;
  selected?: boolean;
  onClick?: () => void;
};

/** A crop's name with its colour dot. The only place crop colours appear next to text. */
export default function CropChip({ crop, selected = false, onClick }: CropChipProps) {
  const look = selected ? "bg-brand-tint" : "bg-surface ring-1 ring-hairline ring-inset";
  const content = (
    <>
      <span aria-hidden className="size-2 rounded-pill" style={{ background: cropColor(crop) }} />
      {cropLabel(crop)}
    </>
  );
  const className = `inline-flex items-center gap-1 rounded-pill px-3 py-1 text-small text-ink ${look}`;
  if (!onClick) return <span className={className}>{content}</span>;
  return (
    <button type="button" aria-pressed={selected} onClick={onClick} className={`${className} min-h-11 transition duration-150 ease-ui`}>
      {content}
    </button>
  );
}
