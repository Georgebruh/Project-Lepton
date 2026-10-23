import type { MultiPolygon, Polygon } from 'geojson'
import type { LonLat } from '../exposed/nearest.ts'

/*
 * F15: the barangay report's maps, as geometry in millimetres on the page. Plain functions, no
 * PDF. A point's longitude and latitude become x and y as on Home's preview map: a degree of
 * longitude is shorter than a degree of latitude by cos(latitude), so x is shrunk by that at
 * the view's middle (over a city this small, the same as the app's Web Mercator map).
 */

/** A box on the page, in mm from its top left corner. */
export type Box = { x: number; y: number; width: number; height: number }

/** Bounds in degrees: west, south, east, north. */
export type Bounds = [west: number, south: number, east: number, north: number]

/** What a map shows: the bounds in view, where a point lies on the page, and how many mm a km takes. */
export type MapView = { bounds: Bounds; toPage: (point: LonLat) => [x: number, y: number]; mmPerKm: number }

/** Kilometres in a degree of latitude (and of longitude at the equator), near enough for a map's scale. */
const KM_PER_DEGREE = 111.32

/** The lengths a scale bar may show, in km. */
const SCALE_LENGTHS_KM = [0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10]

/** A shape's rings, every part's outer ring and its holes, as [longitude, latitude] points. */
export function ringsOf(geometry: Polygon | MultiPolygon): LonLat[][] {
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates
  return polygons.flatMap((polygon) => polygon.map((ring) => ring.map(([lon, lat]): LonLat => [lon, lat])))
}

/** The bounds of some points. */
export function boundsOf(points: LonLat[]): Bounds {
  let [west, south, east, north] = [Infinity, Infinity, -Infinity, -Infinity]
  for (const [lon, lat] of points) {
    west = Math.min(west, lon)
    east = Math.max(east, lon)
    south = Math.min(south, lat)
    north = Math.max(north, lat)
  }
  return [west, south, east, north]
}

/** Whether two bounds overlap. */
export function overlaps(a: Bounds, b: Bounds): boolean {
  return a[0] <= b[2] && b[0] <= a[2] && a[1] <= b[3] && b[1] <= a[3]
}

/** Whether a point lies inside bounds. */
export function contains([west, south, east, north]: Bounds, [lon, lat]: LonLat): boolean {
  return west <= lon && lon <= east && south <= lat && lat <= north
}

/**
 * The view that fits `bounds` into `box`: widened by `pad` of its size on each side and to at
 * least `minKm` across, then to the box's shape, so nothing is stretched. The middle of
 * `bounds` stays at the middle of the box.
 */
export function fitView(bounds: Bounds, box: Box, pad: number, minKm: number): MapView {
  const [west, south, east, north] = bounds
  const middle: LonLat = [(west + east) / 2, (south + north) / 2]
  const shrink = Math.cos((middle[1] * Math.PI) / 180)
  // The bounds' size in km, padded, at least minKm, then shaped like the box
  let wide = Math.max((east - west) * shrink * KM_PER_DEGREE * (1 + 2 * pad), minKm)
  let tall = Math.max((north - south) * KM_PER_DEGREE * (1 + 2 * pad), minKm)
  if (wide / tall < box.width / box.height) {
    wide = (tall * box.width) / box.height
  } else {
    tall = (wide * box.height) / box.width
  }
  const mmPerKm = box.width / wide
  const halfLon = wide / 2 / (shrink * KM_PER_DEGREE)
  const halfLat = tall / 2 / KM_PER_DEGREE
  return {
    bounds: [middle[0] - halfLon, middle[1] - halfLat, middle[0] + halfLon, middle[1] + halfLat],
    toPage: ([lon, lat]) => [
      box.x + box.width / 2 + (lon - middle[0]) * shrink * KM_PER_DEGREE * mmPerKm,
      box.y + box.height / 2 - (lat - middle[1]) * KM_PER_DEGREE * mmPerKm,
    ],
    mmPerKm,
  }
}

/** The scale bar's length in km: the shortest round length that is at least `minMm` long on the map. */
export function scaleKm(mmPerKm: number, minMm: number): number {
  return SCALE_LENGTHS_KM.find((km) => km * mmPerKm >= minMm) ?? SCALE_LENGTHS_KM[SCALE_LENGTHS_KM.length - 1]
}

/**
 * A ring as points on the page, leaving out each point closer than `stepMm` to the last one
 * kept (the ring's last point is always kept), so a small map carries no detail it cannot show.
 */
export function pagePoints(ring: LonLat[], view: MapView, stepMm: number): [x: number, y: number][] {
  const points: [number, number][] = []
  ring.forEach((point, i) => {
    const [x, y] = view.toPage(point)
    const last = points[points.length - 1]
    if (!last || i === ring.length - 1 || Math.hypot(x - last[0], y - last[1]) >= stepMm) {
      points.push([x, y])
    }
  })
  return points
}
