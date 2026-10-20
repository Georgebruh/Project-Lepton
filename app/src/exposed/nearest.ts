import type { MultiPolygon, Polygon } from 'geojson'

/**
 * F8: the health centers nearest a point, the barangay a point lies in, and the search for a
 * barangay by name. Plain functions, no React. Points are [longitude, latitude] in degrees
 * (WGS84), as in F2's files. Everything here runs on the phone: the reader's location and
 * answers are never sent anywhere.
 */

/** A point: longitude, then latitude, in degrees (GeoJSON's order). */
export type LonLat = [lon: number, lat: number]

/** The Earth's mean radius in km (IUGG), for the haversine distance. */
const EARTH_RADIUS_KM = 6371.0088

/**
 * The straight-line distance between two points, in km: the haversine formula, the shortest
 * path over a sphere with the Earth's mean radius. Across Quezon City it differs from a map's
 * measuring tool by a few metres at most, which the list's 0.1 km steps do not show.
 */
export function distanceKm([lon1, lat1]: LonLat, [lon2, lat2]: LonLat): number {
  const rad = Math.PI / 180
  const dLat = (lat2 - lat1) * rad
  const dLon = (lon2 - lon1) * rad
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(h))
}

/** The `count` places nearest a point, nearest first, each with its distance in km. */
export function nearestPlaces<P extends { lon: number; lat: number }>(
  places: P[],
  from: LonLat,
  count: number,
): (P & { km: number })[] {
  return places
    .map((place) => ({ ...place, km: distanceKm(from, [place.lon, place.lat]) }))
    .sort((a, b) => a.km - b.km)
    .slice(0, count)
}

/**
 * Whether a point lies inside a shape, given all its rings (outer rings and holes): a line from
 * the point due east crosses the rings an odd number of times when the point is inside, so a
 * hole takes its area out of the shape.
 */
export function insideRings(rings: LonLat[][], [x, y]: LonLat): boolean {
  let inside = false
  for (const ring of rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i]
      const [xj, yj] = ring[j]
      if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
        inside = !inside
      }
    }
  }
  return inside
}

/**
 * A point inside a polygon (its outer ring and holes), near its middle: on the latitude halfway
 * between its north and south edges, the middle of the widest stretch of that line that lies
 * inside the polygon. Unlike the centroid, it is always inside, even for a crescent.
 */
export function middlePoint(polygon: LonLat[][]): LonLat {
  const lats = polygon[0].map(([, lat]) => lat)
  const y = (Math.min(...lats) + Math.max(...lats)) / 2
  // Where the rings' edges cross that latitude, west to east; inside between crossings 1-2, 3-4, ...
  const crossings: number[] = []
  for (const ring of polygon) {
    for (let i = 1; i < ring.length; i++) {
      const [x1, y1] = ring[i - 1]
      const [x2, y2] = ring[i]
      if (y1 > y !== y2 > y) {
        crossings.push(x1 + ((y - y1) / (y2 - y1)) * (x2 - x1))
      }
    }
  }
  crossings.sort((a, b) => a - b)
  let west = crossings[0]
  let east = crossings[1]
  for (let i = 2; i + 1 < crossings.length; i += 2) {
    if (crossings[i + 1] - crossings[i] > east - west) {
      west = crossings[i]
      east = crossings[i + 1]
    }
  }
  return [(west + east) / 2, y]
}

/** A GeoJSON shape's parts, each a polygon of rings, as [longitude, latitude] points. */
export function shapeParts(geometry: Polygon | MultiPolygon): LonLat[][][] {
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates
  return polygons.map((polygon) => polygon.map((ring) => ring.map(([lon, lat]): LonLat => [lon, lat])))
}

/**
 * A point inside a shape of one or more parts (each a polygon: its outer ring and any holes),
 * near the middle of its largest part (middlePoint). F8 starts the distances from a picked
 * barangay there; F11's map list shows a barangay's or a city's tooltip there.
 */
export function shapeMiddle(polygons: LonLat[][][]): LonLat {
  const largest = polygons.reduce((big, part) => (ringArea(part[0]) > ringArea(big[0]) ? part : big))
  return middlePoint(largest)
}

/** A ring's area in square degrees (the shoelace formula), to find a shape's largest part. */
export function ringArea(ring: LonLat[]): number {
  let twice = 0
  for (let i = 1; i < ring.length; i++) {
    twice += ring[i - 1][0] * ring[i][1] - ring[i][0] * ring[i - 1][1]
  }
  return Math.abs(twice) / 2
}

/** A distance as the list writes it: "0.4 km", "12 km"; below 0.1 km, "under 0.1 km". */
export function formatKm(km: number): string {
  if (km < 0.05) {
    return 'under 0.1 km'
  }
  return km < 9.95 ? `${km.toFixed(1)} km` : `${Math.round(km)} km`
}

/**
 * A link that opens Google Maps (the app on a phone, the website elsewhere) with directions to a
 * point. Only the destination is in the link: Maps finds the start itself, with the phone's own
 * permission, so LEPTON never hands on the reader's location.
 * https://developers.google.com/maps/documentation/urls/get-started#directions-action
 */
export function directionsUrl([lon, lat]: LonLat): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}`
}

/** Short forms residents type, and the word in the barangay's name they stand for. */
const SHORT_WORDS: Record<string, string> = { sto: 'santo', sta: 'santa', st: 'saint' }

/** Words a search ignores: "Brgy. Tatalon" finds Tatalon. */
const SKIPPED_WORDS = new Set(['barangay', 'brgy', 'bgy'])

/**
 * A name or a search as words to compare: no accents ("Doña" matches "dona"), no dots ("U.P."
 * is "up"), lower case, split on anything that is not a letter or a digit.
 */
export function searchWords(text: string): string[] {
  return text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replaceAll('.', '')
    .split(/[^a-z0-9]+/)
    .filter((word) => word !== '' && !SKIPPED_WORDS.has(word))
}

/**
 * The places whose name matches what the reader typed, at most `limit`, best first: a name
 * matches when each typed word begins one of its words ("sto dom" finds "Santo Domingo
 * (Matalahib)"), or when the typed letters run together inside it ("pagasa" finds "Bagong
 * Pag-asa"). Names that begin with the first typed word come first, then A to Z.
 */
export function matchPlaces<P extends { name: string }>(places: P[], typed: string, limit: number): P[] {
  const typedWords = searchWords(typed).map((word) => SHORT_WORDS[word] ?? word)
  if (typedWords.length === 0) {
    return []
  }
  const joined = typedWords.join('')
  return places
    .map((place) => ({ place, words: searchWords(place.name) }))
    .filter(
      ({ words }) =>
        typedWords.every((word) => words.some((own) => own.startsWith(word))) || words.join('').includes(joined),
    )
    .sort(
      (a, b) =>
        Number(!a.words[0].startsWith(typedWords[0])) - Number(!b.words[0].startsWith(typedWords[0])) ||
        a.place.name.localeCompare(b.place.name),
    )
    .slice(0, limit)
    .map(({ place }) => place)
}
