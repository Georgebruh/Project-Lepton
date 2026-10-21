/**
 * F4: the ids of the cities' GeoJSON source and of its four layers, which CityMap.tsx draws.
 * F5's barangay layers (barangayLayers.ts) go between them: above the open city's fill, which
 * fades out under the barangays, and below the open city's outline, which stays on top.
 */
export const CITY_SOURCE = 'cities'

export const CITY_LAYERS = {
  /** Every city but the open one: its fill and its outline. */
  fill: 'cities-fill',
  line: 'cities-line',
  /** The open city (Quezon City, at levels 2 and 3): its fill and its outline. */
  openFill: 'city-open-fill',
  openLine: 'city-open-line',
}
