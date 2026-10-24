import { useMemo } from 'react'
import type { GuideBarangay } from './guideData.ts'
import type { LonLat } from './nearest.ts'
import './GuideMap.css'

/** The map's size, px; on screen it keeps these proportions at any width. */
const WIDTH = 390
const HEIGHT = 280

/** Space kept clear around the reader and the health centers, px, so no marker touches the edge. */
const MARGIN = 36

/** The map never zooms in closer than this many km across its height. */
const MIN_SPAN_KM = 1.2

/** Kilometres per degree of latitude, on the Earth's mean radius (as nearest.ts measures). */
const KM_PER_DEGREE = (Math.PI * 6371.0088) / 180

type GuideMapProps = {
  barangays: GuideBarangay[]
  /** The barangay to outline: the one the reader is in, or picked. */
  focus?: GuideBarangay
  /** The reader's position, or null when the reader picked a barangay. */
  you: LonLat | null
  /** The health centers to number, nearest first. */
  centers: LonLat[]
  /** What the map shows, in words, for screen readers. */
  label: string
}

/** Turns longitude and latitude into the map's px. */
function fitPoints(points: LonLat[]): (point: LonLat) => [number, number] {
  const middleLat = points.reduce((sum, [, lat]) => sum + lat, 0) / points.length
  const kmPerLon = KM_PER_DEGREE * Math.cos((middleLat * Math.PI) / 180)
  const xs = points.map(([lon]) => lon * kmPerLon)
  const ys = points.map(([, lat]) => -lat * KM_PER_DEGREE)
  const [west, east, north, south] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]
  const pxPerKm = Math.min(
    (WIDTH - 2 * MARGIN) / Math.max(east - west, 1e-9),
    (HEIGHT - 2 * MARGIN) / Math.max(south - north, 1e-9),
    HEIGHT / MIN_SPAN_KM,
  )
  const [centerX, centerY] = [(west + east) / 2, (north + south) / 2]
  return ([lon, lat]) => [
    WIDTH / 2 + (lon * kmPerLon - centerX) * pxPerKm,
    HEIGHT / 2 + (-lat * KM_PER_DEGREE - centerY) * pxPerKm,
  ]
}

/** A ring as SVG path data, in the map's px. */
function ringPath(ring: LonLat[], toPx: (point: LonLat) => [number, number]): string {
  return `M${ring.map((point) => toPx(point).map((v) => v.toFixed(1)).join(' ')).join('L')}Z`
}

/** Whether a barangay's bounding box overlaps the map: one wholly off it is not drawn. */
function onMap(rings: LonLat[][], toPx: (point: LonLat) => [number, number]): boolean {
  const pxs = rings.flat().map(toPx)
  const xs = pxs.map(([x]) => x)
  const ys = pxs.map(([, y]) => y)
  return Math.max(...xs) >= 0 && Math.min(...xs) <= WIDTH && Math.max(...ys) >= 0 && Math.min(...ys) <= HEIGHT
}

/** The map of step 3: Quezon City's barangays around the reader. */
export default function GuideMap({ barangays, focus, you, centers, label }: GuideMapProps) {
  const { paths, focusPath, youPx, centerPxs } = useMemo(() => {
    const shown = [...(you ? [you] : []), ...centers, ...(focus ? focus.rings.flat() : [])]
    const toPx = fitPoints(shown)
    return {
      paths: barangays
        .filter(({ rings }) => onMap(rings, toPx))
        .map(({ psgc, rings }) => ({ psgc, d: rings.map((ring) => ringPath(ring, toPx)).join('') })),
      focusPath: focus ? focus.rings.map((ring) => ringPath(ring, toPx)).join('') : null,
      youPx: you ? toPx(you) : null,
      centerPxs: centers.map(toPx),
    }
  }, [barangays, focus, you, centers])

  /** A marker's place, as a share of the map's width and height, so it follows the map's size. */
  const at = ([x, y]: [number, number]) => ({ left: `${(x / WIDTH) * 100}%`, top: `${(y / HEIGHT) * 100}%` })

  return (
    <div className="guide-map" role="img" aria-label={label}>
      <svg className="guide-map-svg" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} aria-hidden="true">
        {paths.map(({ psgc, d }) => (
          <path key={psgc} d={d} className="guide-map-barangay" />
        ))}
        {focusPath && <path d={focusPath} className="guide-map-focus" />}
      </svg>
      {youPx && <span className="guide-map-you" style={at(youPx)} />}
      {/* Drawn last to first, so the nearest center's number lies on top */}
      {centerPxs
        .map((px, i) => (
          <span key={i} className="guide-map-center label-ui-s" style={at(px)} aria-hidden="true">
            {i + 1}
          </span>
        ))
        .reverse()}
    </div>
  )
}
