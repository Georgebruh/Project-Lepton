import Badge from '../components/Badge.tsx'
import { LEVEL_NAMES } from './forecast.ts'
import type { CityForecast } from './mapData.ts'
import './OutbreakLegend.css'

type OutbreakLegendProps = {
  /** The outbreak levels, lowest first (city_forecast.json). */
  levels: CityForecast['levels']
  /** The amber badge's words while the week shown is simulated (the city colors are Layer 1 numbers too). */
  simulated: string | null
}

/** The map's legend at levels 1 and 2: the color of each outbreak level and of a city without data. */
export default function OutbreakLegend({ levels, simulated }: OutbreakLegendProps) {
  return (
    <div className="outbreak-legend">
      {simulated && (
        <Badge tone="warn" className="outbreak-legend-badge">
          {simulated}
        </Badge>
      )}
      <p className="outbreak-legend-title label-ui-s">Chance of an outbreak next week</p>
      <ul className="outbreak-legend-levels body-s">
        {levels.map(({ level }) => (
          <li key={level}>
            <span className={`outbreak-legend-swatch outbreak-legend-swatch-${level}`} aria-hidden="true" />
            {LEVEL_NAMES[level]}
          </li>
        ))}
        <li>
          <span className="outbreak-legend-swatch outbreak-legend-swatch-none" aria-hidden="true" />
          No data yet
        </li>
      </ul>
    </div>
  )
}
