# Focused Map Cartography Design

## Objective

Make footprint movement visually legible by focusing every map on the result area, adding distance calibration, and printing comparison displacement on the map.

## Fixed display extent

All single and comparison maps use a fixed display extent of latitude −50° to +5° and longitude −95° to +10°. This is substantially tighter than the scientific source region while retaining every selected cell across the 340 canonical configurations. The fixed extent keeps Map A and Map B visually comparable. The underlying payload region and scientific calculations remain unchanged.

Map cells, geography, guides, footprint boundaries, and inspection highlights are clipped to the display plot. Grid cell sizes and projections use the display extent.

## Scale bar

Every map includes a 500 km scale bar near the lower-left plot edge. Its rendered width uses an equirectangular longitude conversion at the fixed reference latitude of −25°, and the label states `500 km at 25°S` so the latitude dependency is explicit. This is cartographic display geometry, not a scientific output metric.

## Comparison annotation

The map renderer accepts an optional centroid label. Single-map mode retains `Flux-weighted centroid`. In comparison mode, Map A displays `A centroid`; Map B displays `→ N km from A`, using the Python-precomputed `centroid_distance_km` rounded to the nearest kilometre. No browser-side displacement calculation is permitted.

## Explicit method controls

All applicable method settings remain visible below the focal experiment choice. Grid resolution, mean/median statistic, and percentile threshold are ordinary controls rather than collapsed advanced settings.

## Verification

Automated tests assert the fixed projection extent, clipped scientific layers, 500 km scale-bar label and width, and exact use of the stored comparison distance in the Map B annotation. Visual verification covers desktop and 320 px comparison layouts and confirms no console errors or horizontal overflow.
