import { scaleLinear, scalePoint } from 'd3-scale'
import type { CSSProperties } from 'react'
import Badge from '../components/Badge.tsx'
import { SIMULATED_LABEL, formatWeek, rangePercent } from '../map/forecast.ts'
import type { CityForecast, ForecastWeek } from '../map/mapData.ts'
import type { Loaded } from './homeData.ts'
import './BacktestChart.css'

/** How many weeks the chart shows: the latest in the backtest. */
const WEEKS = 36

/** The plot's size in px: 576 wide, counts standing on a line 180 down. */
const WIDTH = 576
const HEIGHT = 196
const BASE = 180
/** The space kept above the tallest mark. */
const TOP = 8
/** Each week's bar is 8 px wide. */
const BAR = 8

type BacktestChartProps = {
  /** The forecasts (city_forecast.json), while it loads undefined, or "failed". */
  forecast: Loaded<CityForecast>
}

/** Home's chart of the city forecast. */
export default function BacktestChart({ forecast }: BacktestChartProps) {
  if (forecast === 'failed') {
    return <p className="backtest-chart-status body-s">The chart could not load.</p>
  }
  if (!forecast) {
    return <div className="backtest-chart backtest-chart-loading" aria-hidden="true" />
  }
  const weeks = forecast.weeks.slice(-WEEKS)
  const model = forecast.map_model
  const x = scalePoint<number>()
    .domain(weeks.map((week) => week.week_index))
    .range([BAR / 2, WIDTH - BAR / 2])
  const at = (week: ForecastWeek) => x(week.week_index) ?? 0
  const tallest = Math.max(
    1,
    ...weeks.flatMap((week) => [week.y ?? 0, week.threshold, week.forecasts[model].high, week.forecasts[model].mu]),
  )
  const y = scaleLinear().domain([0, tallest]).range([BASE, TOP])

  /** A line through each week's value, as SVG path data. */
  const line = (rows: ForecastWeek[], value: (week: ForecastWeek) => number, start = 'M') =>
    rows.map((week, i) => `${i ? 'L' : start}${at(week).toFixed(1)} ${y(value(week)).toFixed(1)}`).join('')
  const range = line(weeks, (week) => week.forecasts[model].high) +
    line([...weeks].reverse(), (week) => week.forecasts[model].low, 'L') + 'Z'

  const first = weeks[0]
  const last = weeks[weeks.length - 1]
  const crossed = weeks.filter((week) => week.breached).length
  const label =
    `Weekly leptospirosis cases in Quezon City, ${formatWeek(first.start, last.end)}` +
    `${forecast.simulated ? ', simulated' : ''}: bars are each week's count; the line is ${model}'s ` +
    `forecast made the week before, shaded across its ${rangePercent(forecast)} range; the amber line is ` +
    `the epidemic threshold, crossed in ${crossed} of ${weeks.length} weeks.`

  return (
    <figure className="backtest-chart">
      <svg className="backtest-chart-plot" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={label}>
        <rect className="backtest-chart-axis" x={0} y={BASE} width={WIDTH} height={1} />
        {/* city_forecast.json's weeks all have a count; only the map's Simulation mode adds weeks without one */}
        {weeks.map(
          (week, i) =>
            week.y !== null && (
              <rect
                key={week.week_index}
                className="backtest-chart-bar"
                x={at(week) - BAR / 2}
                y={y(week.y)}
                width={BAR}
                height={BASE - y(week.y)}
                // Its place from left to right, 0 to 1, for when it grows (BacktestChart.css)
                style={{ '--backtest-chart-at': i / Math.max(1, weeks.length - 1) } as CSSProperties}
              />
            ),
        )}
        <path className="backtest-chart-range" d={range} />
        <path className="backtest-chart-forecast" d={line(weeks, (week) => week.forecasts[model].mu)} />
        <path className="backtest-chart-threshold" d={line(weeks, (week) => week.threshold)} />
      </svg>
      {forecast.simulated && (
        <Badge tone="warn" className="backtest-chart-badge">
          {SIMULATED_LABEL}
        </Badge>
      )}
    </figure>
  )
}
