/**
 * F4: the ids of the cities' GeoJSON source and of its four layers, which CityMap.tsx draws.
 * F5's barangay layers (barangayLayers.ts) go between them: above the open city's fill, which
 * fades out under the barangays, and below the open city's outline, which stays on top.
 * F13: the fills sit over the street map's roads and under its names (layerOrder.ts), the outlines on top.
 */
export const CITY_SOURCE = 'cities'

/** F13: the cities' label points, for the room their names keep (CityMap's addNameRoom). */
export const CITY_NAMES_SOURCE = 'city-names'

export const CITY_LAYERS = {
  /** Every city but the open one: its fill and its outline. */
  fill: 'cities-fill',
  line: 'cities-line',
  /** The open city (Quezon City, at levels 2 and 3): its fill and its outline. */
  openFill: 'city-open-fill',
  openLine: 'city-open-line',
  /** F13: an invisible copy of the cities' names, on top, that keeps the street map's names off them. */
  names: 'city-names-room',
  /** F14: the outline of the town the map's search found, over a wider light casing, on top of the other outlines. */
  foundCasing: 'city-found-casing',
  foundLine: 'city-found-line',
}
