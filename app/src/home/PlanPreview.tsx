import { useMemo } from 'react'
import { Link } from 'react-router'
import CenterRow, { CenterRowHeader } from '../components/CenterRow.tsx'
import { formatCount, formatDayMonth, formatWeek } from '../map/forecast.ts'
import { centerName, leadWords } from '../map/plan.ts'
import type { BarangayShapes } from '../map/planData.ts'
import { MAP_PATHS } from '../map/routes.ts'
import { stormTitle, type Loaded, type PlanPreviewData } from './homeData.ts'
import './PlanPreview.css'

/** How many health centers the stock list shows (Figma: 5, then "+ 61 more centers"). */
const SHOWN_CENTERS = 5

/** Quezon City's height on the preview, in px (Figma: 500). */
const MAP_HEIGHT = 500

/** Where the barangay outlines come from (A5's barangays_qc.gpkg), as the caption credits them. */
const BOUNDARIES_CREDIT = 'Boundaries: PSA and NAMRIA, via OCHA’s COD-AB on HDX (CC BY-IGO 3.0).'

/**
 * Each barangay's outline as SVG path data, and the drawing's width, with Quezon City MAP_HEIGHT
 * px tall. Longitude and latitude become x and y; a degree of longitude is shorter than one of
 * latitude by cos(latitude), so x is shrunk by that at the city's middle (over a city this small,
 * the same as the map's Web Mercator).
 */
function drawBarangays(shapes: BarangayShapes): { paths: Map<string, string>; width: number } {
  const outlines = shapes.features.map(({ properties, geometry }) => ({
    psgc: properties.psgc,
    rings: (geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates).flat(),
  }))
  let [west, south, east, north] = [Infinity, Infinity, -Infinity, -Infinity]
  for (const [lon, lat] of outlines.flatMap(({ rings }) => rings.flat())) {
    west = Math.min(west, lon)
    east = Math.max(east, lon)
    south = Math.min(south, lat)
    north = Math.max(north, lat)
  }
  const scale = MAP_HEIGHT / (north - south)
  const shrink = Math.cos((((south + north) / 2) * Math.PI) / 180)
  const point = ([lon, lat]: number[]) =>
    `${((lon - west) * shrink * scale).toFixed(1)} ${((north - lat) * scale).toFixed(1)}`
  const paths = new Map(
    outlines.map(({ psgc, rings }) => [psgc, rings.map((ring) => `M${ring.map(point).join('L')}Z`).join('')]),
  )
  return { paths, width: (east - west) * shrink * scale }
}

type PlanPreviewProps = {
  /** The forecast to show, while it loads undefined, or "failed". */
  preview: Loaded<PlanPreviewData>
}

/**
 * F6: Home's preview of the prophylaxis plan, Figma "Product preview" (node 19:291) and its
 * caption: Quezon City's barangays shaded by the share of residents in flood zones in Kristine's
 * forecast 1 day ahead, the flagged barangays outlined, and the stock list beside them. Drawn from
 * F2's files, not a picture (the Home notes: "Product preview is real data"). Stock planning, not
 * prescriptions.
 */
export default function PlanPreview({ preview }: PlanPreviewProps) {
  const data = preview === 'failed' ? undefined : preview
  return (
    <figure className="plan-preview">
      <div className="plan-preview-frame">
        {data ? (
          <>
            <PreviewMap data={data} />
            <Legend data={data} />
            <StockList data={data} />
          </>
        ) : (
          <p className="plan-preview-status body-m">
            {preview === 'failed' ? (
              <>
                The preview could not load. <Link to={MAP_PATHS[3]}>Open the prophylaxis plan</Link> instead.
              </>
            ) : (
              'Loading the preview…'
            )}
          </p>
        )}
      </div>
      {data && (
        <figcaption className="plan-preview-caption body-s">
          The map, forecasting {stormTitle(data.storm)} {leadWords(data.run.lead_days ?? 1)}. Shades show the
          share of each barangay’s residents in flood zones; outlines mark the {data.run.flagged} flagged
          barangays. {BOUNDARIES_CREDIT}
        </figcaption>
      )}
    </figure>
  )
}

type PartProps = { data: PlanPreviewData }

/** The barangays: filled by class, outlined in the map's boundary color; the flagged and the selected on top. */
function PreviewMap({ data }: PartProps) {
  const { paths, width } = useMemo(() => drawBarangays(data.shapes), [data.shapes])
  const { barangays, selected, run } = data
  const flagged = [...barangays.values()].filter((barangay) => barangay.flagged)
  const label =
    `Map of Quezon City's ${barangays.size} barangays, shaded by the share of their residents in flood zones ` +
    `in the forecast of ${stormTitle(data.storm)} ${leadWords(run.lead_days ?? 1)}; ${run.flagged} are flagged.`
  return (
    <div className="plan-preview-map">
      <svg
        className="plan-preview-svg"
        viewBox={`0 0 ${width.toFixed(1)} ${MAP_HEIGHT}`}
        width={Math.round(width)}
        height={MAP_HEIGHT}
        role="img"
        aria-label={label}
      >
        {[...paths].map(([psgc, d]) => (
          <path key={psgc} d={d} className={`plan-preview-barangay plan-preview-class-${barangays.get(psgc)?.class}`} />
        ))}
        {flagged.map(({ psgc }) => (
          <path key={psgc} d={paths.get(psgc)} className="plan-preview-flagged" />
        ))}
        {selected && <path d={paths.get(selected)} className="plan-preview-selected" />}
      </svg>
    </div>
  )
}

/** The legend, Figma "Legend" (node 19:503): the five shades, light to dark. */
function Legend({ data }: PartProps) {
  const { classes } = data
  return (
    <div className="plan-preview-legend">
      <p className="plan-preview-legend-title label-ui-s">
        Residents in flood zones
        <span className="visually-hidden">
          : lightest {classes[0].label}, darkest {classes[classes.length - 1].label}
        </span>
      </p>
      <span className="plan-preview-ramp" aria-hidden="true">
        {classes.map((share) => (
          <span key={share.class} className={`plan-preview-swatch plan-preview-class-${share.class}`} />
        ))}
      </span>
    </div>
  )
}

/** The stock list, Figma "Stock list" (node 19:511): the forecast, two totals and the top health centers. */
function StockList({ data }: PartProps) {
  const { run, flood, needs } = data
  const shown = needs.slice(0, SHOWN_CENTERS)
  return (
    <section className="plan-preview-stock" aria-labelledby="plan-preview-stock-title">
      <p className="plan-preview-issued label-eyebrow">
        {run.issued ? `Forecast issued ${formatDayMonth(run.issued)} · ` : ''}for{' '}
        {formatWeek(run.window.start, run.window.end)}
      </p>
      <h3 id="plan-preview-stock-title" className="heading-m">
        What to send
      </h3>
      <div className="plan-preview-totals">
        <p className="plan-preview-total">
          <span className="plan-preview-total-label label-ui-s">Residents exposed</span>
          <span className="data-l">{formatCount(flood.exposed)}</span>
        </p>
        <p className="plan-preview-total">
          <span className="plan-preview-total-label label-ui-s">Doxycycline 100 mg</span>
          <span className="data-l">{formatCount(flood.doxy100)}</span>
        </p>
      </div>
      <div className="plan-preview-centers" role="table" aria-label="What to send, by health center">
        <CenterRowHeader />
        {shown.map((need) => (
          <CenterRow
            key={need.facilityCode}
            name={centerName(need.name)}
            doxycycline={need.units.doxy100}
            courses={need.units.courses}
            amoxicillin={need.units.amox500}
          />
        ))}
      </div>
      <p className="plan-preview-more body-s">
        + {needs.length - shown.length} more centers · stock planning, not prescriptions
      </p>
    </section>
  )
}
