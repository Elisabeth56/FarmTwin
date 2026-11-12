// Types for the 3D farm module shared by the site and the desktop app.
export type TwinCrop = 'maize' | 'sorghum' | 'rice' | 'cassava' | 'yam' | 'cowpea';
export interface TwinPlot { crop: TwinCrop | string; label?: string }

export interface TwinOptions {
  frame: HTMLElement;
  canvas: HTMLCanvasElement;
  badge: HTMLElement;
  chip: HTMLElement;
  chipDot: HTMLElement;
  chipText: HTMLElement;
  autoRotate?: boolean;
  onReady?: () => void;
  plots?: TwinPlot[];
  badgePlot?: number;
  onDemand?: boolean;
}

export interface Twin {
  setRain(on: boolean): void;
  pause(): void;
  resume(): void;
  dispose(): void;
  setView(azimuth: number, polar?: number): void;
  readonly azimuth: number;
  readonly polar: number;
}

export const LANDING_PLOTS: TwinPlot[];
export function mountTwin(options: TwinOptions): Twin;
