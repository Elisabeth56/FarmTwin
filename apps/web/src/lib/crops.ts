// The six crops FarmTwin covers, in the order the app lists them. Colours come from the tokens.
export const CROPS = ["maize", "cassava", "yam", "sorghum", "rice", "cowpea"] as const;
export type Crop = (typeof CROPS)[number];

export function isCrop(value: string): value is Crop {
  return (CROPS as readonly string[]).includes(value);
}

export function cropColor(crop: string): string {
  return isCrop(crop) ? `var(--crop-${crop})` : "var(--ink-faint)";
}

export function cropLabel(crop: string): string {
  return crop.charAt(0).toUpperCase() + crop.slice(1);
}
