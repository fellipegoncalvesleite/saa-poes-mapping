import type { Region } from "../data/types";

export interface Plot { left: number; top: number; width: number; height: number }

export function createProjection(region: Region, plot: Plot) {
  return {
    x: (lon: number) => plot.left + ((lon - region.lon_min) / (region.lon_max - region.lon_min)) * plot.width,
    y: (lat: number) => plot.top + ((region.lat_max - lat) / (region.lat_max - region.lat_min)) * plot.height,
  };
}
