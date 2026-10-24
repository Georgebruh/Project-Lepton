import { FLOOD_LEVELS, type FloodPeriod } from './floodLayer.ts'
import './FloodLegend.css'

type FloodLegendProps = {
  /** The NOAH map shown: the rain that comes once in this many years. */
  period: FloodPeriod
  /** The line saying only one city's zones are shown, and how to see the rest; null: every zone. */
  only: string | null
}

/** The flood zones' legend. */
export default function FloodLegend({ period, only }: FloodLegendProps) {
  return (
    <div className="flood-legend">
      <p className="flood-legend-title label-ui-s">Flood hazard · NOAH {period}-year rain</p>
      {only && <p className="flood-legend-only body-s">{only}</p>}
      <ul className="flood-legend-levels body-s">
        {FLOOD_LEVELS.map(({ level, name, depth }) => (
          <li key={level}>
            <span className={`flood-legend-swatch flood-legend-swatch-${level}`} aria-hidden="true" />
            <span>
              {name}
              <span className="flood-legend-depth"> · {depth}</span>
            </span>
          </li>
        ))}
      </ul>
      <p className="flood-legend-credit body-s">UP NOAH Center · all provinces mapped · ODbL · simplified for display</p>
    </div>
  )
}
