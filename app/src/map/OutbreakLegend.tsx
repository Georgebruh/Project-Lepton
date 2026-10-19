import Badge from '../components/Badge.tsx'
import { LEVEL_NAMES, SIMULATED_LABEL } from './forecast.ts'
import type { CityForecast } from './mapData.ts'
import './OutbreakLegend.css'

type OutbreakLegendProps = {
  /** The outbreak levels, lowest first (city_forecast.json). */
  levels: CityForecast['levels']
  /** Whether the forecasts are simulated: the city colors are Layer 1 numbers too. */
  simulated: boolean
}

/**
 * F4: the map's legend at levels 1 and 2, Figma "Legend" (node 55:349): the color of each
 * outbreak level and of a city without data. While the forecasts are simulated it carries the
 * amber badge, because the city colors come from them (app check U2); Figma's legend has none.
 */
export default function OutbreakLegend({ levels, simulated }: OutbreakLegendProps) {
  return (
    <div className="outbreak-legend">
      {simulated && (
        <Badge tone="warn" className="outbreak-legend-badge">
          {SIMULATED_LABEL}
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
