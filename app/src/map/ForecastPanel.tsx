import { useLocation } from 'react-router'
import { compareLink } from '../compare/periods.ts'
import Badge from '../components/Badge.tsx'
import Button from '../components/Button.tsx'
import {
  LEVEL_NAMES,
  LEVEL_TONES,
  SIMULATED_LABEL,
  formatChance,
  formatWeek,
  levelOf,
  rangePercent,
  thresholdCount,
  weeksBefore,
} from './forecast.ts'
import type { CityForecast, ForecastWeek } from './mapData.ts'
import PanelModes from './PanelModes.tsx'
import { MAP_PATHS } from './routes.ts'
import WeeklyCasesChart from './WeeklyCasesChart.tsx'
import './ForecastPanel.css'

/** How many past weeks the chart shows (Figma: "Last 15 weeks"). */
const PAST_WEEKS = 15

type ForecastPanelProps = {
  /** The city's name, as the heading writes it. */
  city: string
  forecast: CityForecast
  /** The week after the chosen date, or undefined if the backtest has no forecast for it. */
  week: ForecastWeek | undefined
}

/**
 * F4: the city panel's case forecast, Figma frame 2's "Panel" (node 53:316): next week's
 * expected cases with the range, the chance of an outbreak (a count above the epidemic
 * threshold) with its level, the last 15 weeks and next week's range, then the Prophylaxis
 * plan and Compare models buttons. Every number is the map model's (M4) for the chosen week in
 * city_forecast.json; the expected count is rounded to whole cases. While the file says
 * simulated, the amber badge sits above the numbers. F9: Compare models opens at the year of
 * the week shown.
 */
export default function ForecastPanel({ city, forecast, week }: ForecastPanelProps) {
  const { search } = useLocation()
  const model = week?.forecasts[forecast.map_model]
  return (
    <div className="forecast-panel">
      <PanelModes mode="cases" />
      <div className="forecast-panel-heading">
        <h2 className="heading-l">{city}</h2>
        <p className="forecast-panel-subtitle label-ui-s">Cases forecast · next week · whole city</p>
      </div>
      {forecast.simulated && (
        <Badge tone="warn" className="forecast-panel-badge">
          {SIMULATED_LABEL}
        </Badge>
      )}
      {week && model ? (
        <ForecastNumbers forecast={forecast} week={week} />
      ) : (
        <p className="forecast-panel-none body-m">
          No forecast for the week after this date. Choose another date.
        </p>
      )}
      <div className="forecast-panel-actions">
        <Button to={MAP_PATHS[3] + search} icon="arrow-right" className="forecast-panel-action">
          Prophylaxis plan
        </Button>
        <Button variant="secondary" to={week ? compareLink(week.year) : '/compare'} className="forecast-panel-action">
          Compare models
        </Button>
      </div>
    </div>
  )
}

type ForecastNumbersProps = {
  forecast: CityForecast
  week: ForecastWeek
}

/** The panel's numbers for one week: the forecast, the chance of an outbreak and the chart. */
function ForecastNumbers({ forecast, week }: ForecastNumbersProps) {
  const model = week.forecasts[forecast.map_model]
  const level = levelOf(model.p_breach, forecast.levels)
  const chance = formatChance(model.p_breach)
  const threshold = thresholdCount(week.threshold)
  const rangeName = rangePercent(forecast)
  const dates = formatWeek(week.start, week.end)
  const expected = Math.round(model.mu)
  return (
    <>
      <div className="forecast-panel-forecast">
        <p className="forecast-panel-number">
          <span className="data-xl">{expected}</span>
          <span className="forecast-panel-muted body-m">cases expected</span>
        </p>
        <p className="forecast-panel-muted body-s">
          Week of {dates} · {rangeName} range {model.low}–{model.high}
        </p>
      </div>
      <section className="forecast-panel-chance" aria-label="Chance of an outbreak">
        <div className="forecast-panel-chance-head">
          <h3 className="label-ui">Chance of an outbreak</h3>
          <Badge tone={LEVEL_TONES[level]}>{LEVEL_NAMES[level]}</Badge>
        </div>
        <p className="forecast-panel-number forecast-panel-chance-value">
          <span className="data-l">{chance}</span>
          <span className="forecast-panel-muted body-s">above the epidemic threshold ({threshold} cases)</span>
        </p>
        <div className="forecast-panel-chance-bar" aria-hidden="true">
          <div
            className={`forecast-panel-chance-fill forecast-panel-chance-fill-${level}`}
            style={{ width: `${model.p_breach * 100}%` }}
          />
        </div>
      </section>
      <WeeklyCasesChart
        past={weeksBefore(forecast, week, PAST_WEEKS)}
        pastWeeks={PAST_WEEKS}
        next={model}
        threshold={week.threshold}
        rangeName={rangeName}
      />
      {/* Read out when the reader picks another date (Figma has no text here) */}
      <p className="visually-hidden" aria-live="polite">
        Week of {dates}: {expected} cases expected, {rangeName} range {model.low} to {model.high}; {chance} chance
        of an outbreak, {LEVEL_NAMES[level]}.{forecast.simulated ? ` ${SIMULATED_LABEL}.` : ''}
      </p>
    </>
  )
}
