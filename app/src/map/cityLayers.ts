/** The ids of the cities' GeoJSON source and of its four layers. */
export const CITY_SOURCE = 'cities'

/** The cities' label points, for the room their names keep (CityMap's addNameRoom). */
export const CITY_NAMES_SOURCE = 'city-names'

export const CITY_LAYERS = {
  /** Every city but the open one: its fill and its outline. */
  fill: 'cities-fill',
  line: 'cities-line',
  /** The open city (Quezon City, at levels 2 and 3): its fill and its outline. */
  openFill: 'city-open-fill',
  openLine: 'city-open-line',
  /** An invisible copy of the cities' names, on top, that keeps the street map's names off them. */
  names: 'city-names-room',
  /** The outline of the town the map's search found. */
  foundCasing: 'city-found-casing',
  foundLine: 'city-found-line',
}
