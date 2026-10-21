import type { Map as MapLibreMap } from 'maplibre-gl'

/*
 * F13: the order the map draws its layers in, bottom to top, kept in one place:
 *   1. the base map's land, water, parks and buildings (basemap.ts);
 *   2. SLOTS.base     satellite imagery or hill shading, when chosen;
 *   3. the base map's roads;
 *   4. SLOTS.fills    LEPTON's fills: the cities (CityMap) and F5's barangays (barangayLayers.ts),
 *                     over the roads, which would clutter the barangay colors (as in Figma);
 *   5. SLOTS.flood    NOAH's flood zones;
 *   6. SLOTS.weather  clouds, radar and rain;
 *   7. the base map's names, so places and streets stay readable over everything;
 *   8. LEPTON's outlines, on top of everything.
 * A slot is an empty layer that draws nothing. A module adds its layers just below its slot
 * (map.addLayer(layer, SLOTS.fills)), so they land in this order whatever order they are added in.
 */
export const SLOTS = {
  base: 'slot-base',
  fills: 'slot-fills',
  flood: 'slot-flood',
  weather: 'slot-weather',
} as const

/**
 * Adds the slots: the base slot just under the base map's first road, the others just under
 * its first name. Without a base map (it did not load) they all go on top, in order.
 */
export function addSlots(map: MapLibreMap) {
  const layers = map.getStyle().layers
  const firstRoad = layers.find((layer) => 'source-layer' in layer && layer['source-layer'] === 'transportation')?.id
  const firstName = layers.find((layer) => layer.type === 'symbol')?.id
  const slot = (id: string, before: string | undefined) =>
    map.addLayer({ id, type: 'background', layout: { visibility: 'none' } }, before)
  slot(SLOTS.base, firstRoad)
  slot(SLOTS.fills, firstName)
  slot(SLOTS.flood, firstName)
  slot(SLOTS.weather, firstName)
}
