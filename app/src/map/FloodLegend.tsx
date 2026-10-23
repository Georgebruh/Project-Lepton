import { FLOOD_LEVELS, type FloodPeriod } from './floodLayer.ts'
import './FloodLegend.css'

type FloodLegendProps = {
  /** The NOAH map shown: the rain that comes once in this many years. */
  period: FloodPeriod
}

/**
 * F13: the flood zones' legend, Figma "Flood legend" (Components page): NOAH's three hazard
 * levels in the map's blues, which map is shown, and its source. It stands above the map's own
 * legend while the flood zones are on (MapLayout). The zones are simplified for the browser;
 * LEPTON's numbers use NOAH's full maps (app README). F14: the whole Philippines.
 */
export default function FloodLegend({ period }: FloodLegendProps) {
  return (
    <div className="flood-legend">
      <p className="flood-legend-title label-ui-s">Flood hazard · NOAH {period}-year rain</p>
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
