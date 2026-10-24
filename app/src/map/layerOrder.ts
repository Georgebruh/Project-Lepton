import type { Map as MapLibreMap } from 'maplibre-gl'

/* The order the map draws its layers in, bottom to top, kept in one place. */
export const SLOTS = {
  base: 'slot-base',
  fills: 'slot-fills',
  flood: 'slot-flood',
  weather: 'slot-weather',
  buildings: 'slot-buildings',
} as const

/** Adds the slots: the base slot just under the base map's first road. */
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
  slot(SLOTS.buildings, firstName)
}
