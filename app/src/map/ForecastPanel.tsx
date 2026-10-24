import Badge from '../components/Badge.tsx'
import {
  LEVEL_NAMES,
  LEVEL_TONES,
  formatChance,
  formatWeek,
  isSimulated,
  levelOf,
  rangePercent,
  simulatedLabel,
  thresholdCount,
  weeksBefore,
} from './forecast.ts'
import type { CityForecast, ForecastWeek } from './mapData.ts'
import PanelModes from './PanelModes.tsx'
import WeeklyCasesChart from './WeeklyCasesChart.tsx'
import './ForecastPanel.css'

/** How many past weeks the chart shows. */
const PAST_WEEKS = 15

type ForecastPanelProps = {
  /** The city's name, as the heading writes it. */
  city: string
  forecast: CityForecast
  /** The week after the chosen date, or undefined if the backtest has no forecast for it. */
  week: ForecastWeek | undefined
}

/** The city panel's case forecast. */
export default function ForecastPanel({ city, forecast, week }: ForecastPanelProps) {
  const model = week?.forecasts[forecast.map_model]
  const simulated = isSimulated(forecast, week)
  return (
    <div className="forecast-panel">
      <PanelModes mode="cases" />
      <div className="forecast-panel-heading">
        {/* Takes the keyboard when the city opens (MapLayout) */}
        <h2 className="forecast-panel-title heading-l" tabIndex={-1}>
          {city}
        </h2>
        <p className="forecast-panel-subtitle label-ui-s">Cases forecast · next week · whole city</p>
      </div>
      {simulated && (
        <Badge tone="warn" className="forecast-panel-badge">
          {simulatedLabel(forecast)}
        </Badge>
      )}
      {week && model ? (
        <ForecastNumbers forecast={forecast} week={week} />
      ) : (
        <p className="forecast-panel-none body-m">
          No forecast for the week after this date. Choose another date.
        </p>
      )}
      {/* Read out when the reader picks another date. */}
      <p className="visually-hidden" aria-live="polite">
        {week && model ? forecastWords(forecast, week) : 'No forecast for the week after this date.'}
      </p>
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
    </>
  )
}

/** The panel's numbers for one week in one sentence. */
function forecastWords(forecast: CityForecast, week: ForecastWeek): string {
  const model = week.forecasts[forecast.map_model]
  const level = levelOf(model.p_breach, forecast.levels)
  return (
    `Week of ${formatWeek(week.start, week.end)}: ${Math.round(model.mu)} cases expected, ` +
    `${rangePercent(forecast)} range ${model.low} to ${model.high}; ${formatChance(model.p_breach)} chance of an ` +
    `outbreak, ${LEVEL_NAMES[level]}.${isSimulated(forecast, week) ? ` ${simulatedLabel(forecast)}.` : ''}`
  )
}
