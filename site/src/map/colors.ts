const VIRIDIS: Array<[number, [number, number, number]]> = [
  [0, [68, 1, 84]],
  [0.25, [59, 82, 139]],
  [0.5, [33, 145, 140]],
  [0.75, [94, 201, 98]],
  [1, [253, 231, 37]],
];

function interpolate(t: number): string {
  const value = Math.max(0, Math.min(1, t));
  const rightIndex = Math.max(1, VIRIDIS.findIndex(([position]) => value <= position));
  const left = VIRIDIS[rightIndex - 1]!;
  const right = VIRIDIS[rightIndex]!;
  const local = (value - left[0]) / (right[0] - left[0] || 1);
  const channels = left[1].map((channel, index) => Math.round(channel + (right[1][index]! - channel) * local));
  return `rgb(${channels.join(",")})`;
}

export function colorForFlux(value: number | null, domain: [number, number]): string | null {
  if (value === null || !Number.isFinite(value) || value <= 0 || domain[0] <= 0 || domain[1] <= 0) return null;
  const low = Math.log10(domain[0]);
  const high = Math.log10(domain[1]);
  return interpolate(high === low ? 0.5 : (Math.log10(value) - low) / (high - low));
}

export function viridisAt(t: number): string { return interpolate(t); }
