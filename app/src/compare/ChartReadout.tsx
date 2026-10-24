import type { CSSProperties } from 'react'
import Badge from '../components/Badge.tsx'
import { badgeWords } from '../map/forecast.ts'
import type { ForecastWeek } from '../map/mapData.ts'
import type { StormMark } from './periods.ts'
import { stormWords, weekTitle, type ReadoutRow } from './readout.ts'
import SeriesKey from './SeriesKey.tsx'
import './ChartReadout.css'

type ChartReadoutProps = {
  week: ForecastWeek
  /** Its numbers for what the chart shows (readoutRows). */
  rows: ReadoutRow[]
  /** The storm whose flood began that week, if one did. */
  storm: StormMark | undefined
  simulated: boolean
  /** Its place over the plot, beside the crosshair. */
  style: CSSProperties
}

/** The tooltip of the week under the pointer (or the keyboard). */
export default function ChartReadout({ week, rows, storm, simulated, style }: ChartReadoutProps) {
  return (
    <div className="chart-readout" style={style} aria-hidden="true">
      <p className="chart-readout-week label-ui">{weekTitle(week)}</p>
      {/* Also a week the Simulation mode added */}
      {(simulated || week.simulated) && <Badge tone="warn">{badgeWords(simulated)}</Badge>}
      <ul className="chart-readout-rows">
        {rows.map((row) => (
          <li key={row.series} className="chart-readout-row">
            <SeriesKey series={row.series} />
            <span className="chart-readout-value data-m">{row.value}</span>
            <span className="chart-readout-label body-s">
              {row.label}
              {row.note && <span className="chart-readout-note">{row.note}</span>}
            </span>
          </li>
        ))}
      </ul>
      {storm && <p className="chart-readout-storm body-s">{stormWords(storm)}</p>}
    </div>
  )
}
