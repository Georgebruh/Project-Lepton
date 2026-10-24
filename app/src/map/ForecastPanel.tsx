import Badge from '../components/Badge.tsx'
import Facts from './Facts.tsx'
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
import WeeklyCasesChart from './WeeklyCasesChart.tsx'
import WordHelp, { type Word } from './WordHelp.tsx'
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
      <div className="forecast-panel-body">
        {/* Takes the keyboard when the city opens (MapLayout) */}
        <h2 className="forecast-panel-title heading-l" tabIndex={-1}>
          {city}
        </h2>
        {simulated && (
          <Badge tone="warn" className="forecast-panel-badge">
            {simulatedLabel(forecast)}
          </Badge>
        )}
        {week && model ? (
          <ForecastNumbers forecast={forecast} week={week} />
        ) : (
          <p className="forecast-panel-none body-m">No forecast for the week after this date.</p>
        )}
      </div>
      <div className="forecast-panel-foot">
        <WordHelp words={helpWords(city, forecast)} />
      </div>
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
  const rangeName = rangePercent(forecast)
  return (
    <>
      <div className="forecast-panel-forecast">
        <p className="forecast-panel-number">
          <span className="data-xl">{Math.round(model.mu)}</span>
          <span className="forecast-panel-muted body-m">cases expected</span>
        </p>
        <Facts
          facts={[
            { label: 'Week', value: formatWeek(week.start, week.end) },
            { label: `${rangeName} range`, value: `${model.low}–${model.high} cases` },
          ]}
        />
      </div>
      <section className="forecast-panel-chance" aria-label="Chance of an outbreak">
        <div className="forecast-panel-chance-head">
          <h3 className="label-ui">Chance of an outbreak</h3>
          <Badge tone={LEVEL_TONES[level]}>{LEVEL_NAMES[level]}</Badge>
        </div>
        <p className="forecast-panel-chance-value data-l">{formatChance(model.p_breach)}</p>
        <div className="forecast-panel-chance-bar" aria-hidden="true">
          <div
            className={`forecast-panel-chance-fill forecast-panel-chance-fill-${level}`}
            style={{ width: `${model.p_breach * 100}%` }}
          />
        </div>
        <Facts
          className="forecast-panel-chance-facts"
          facts={[{ label: 'Epidemic threshold', value: `${thresholdCount(week.threshold)} cases` }]}
        />
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

/** What the forecast's words mean, for the panel's ? (WordHelp). */
function helpWords(city: string, forecast: CityForecast): Word[] {
  return [
    {
      term: 'Cases expected',
      meaning: `LEPTON's best estimate of how many leptospirosis cases ${city} will report next week.`,
    },
    {
      term: `${rangePercent(forecast)} range`,
      meaning: `The real count should land inside this range in ${rangePercent(forecast)} of weeks.`,
    },
    { term: 'Chance of an outbreak', meaning: "How likely next week's count is to go above the epidemic threshold." },
    {
      term: 'Epidemic threshold',
      meaning:
        'More cases than this is unusual for this week of the year: the average for this week over the past ' +
        'five years, plus a margin for normal ups and downs.',
    },
    { term: forecast.levels.map((step) => LEVEL_NAMES[step.level]).join(', '), meaning: levelMeanings(forecast) },
  ]
}

/** Where each outbreak level starts, in words: "Low, a chance under 10%; Watch, 10% to 49%; High, 50% or more." */
function levelMeanings(forecast: CityForecast): string {
  const steps = forecast.levels.map((step) => ({ name: LEVEL_NAMES[step.level], from: Math.round(step.from * 100) }))
  const parts = steps.map(({ name, from }, i) => {
    const next = steps[i + 1]
    if (!next) {
      return `${name}, ${from}% or more`
    }
    return i === 0 ? `${name}, a chance under ${next.from}%` : `${name}, ${from}% to ${next.from - 1}%`
  })
  return `${parts.join('; ')}.`
}

/** The panel's numbers for one week in one sentence. */
function forecastWords(forecast: CityForecast, week: ForecastWeek): string {
  const model = week.forecasts[forecast.map_model]
  const level = levelOf(model.p_breach, forecast.levels)
  return (
    `Week of ${formatWeek(week.start, week.end)}: ${Math.round(model.mu)} cases expected, ` +
    `${rangePercent(forecast)} range ${model.low} to ${model.high}; ${formatChance(model.p_breach)} chance of an ` +
    `outbreak, ${LEVEL_NAMES[level]}; epidemic threshold ${thresholdCount(week.threshold)} cases.` +
    (isSimulated(forecast, week) ? ` ${simulatedLabel(forecast)}.` : '')
  )
}
