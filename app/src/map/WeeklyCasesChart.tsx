import { scaleBand, scaleLinear } from 'd3-scale'
import type { ForecastWeek, ModelForecast } from './mapData.ts'
import './WeeklyCasesChart.css'

/** The plot's size in px: 351 wide, bars standing on a line 130 down. */
const WIDTH = 351
const HEIGHT = 130
/** Next week's marks are 10 px wide: the range as a bar, the expected count as a square. */
const MARK = 10

/** The past weeks' label under the bars: "Last 15 weeks"; fewer at the backtest's start, none without bars. */
function pastLabel(weeks: number): string | null {
  if (weeks === 0) {
    return null
  }
  return weeks === 1 ? 'Last week' : `Last ${weeks} weeks`
}

type WeeklyCasesChartProps = {
  /** The weeks before next week, oldest first, with their counts (fewer at the start of the backtest). */
  past: ForecastWeek[]
  /** How many past weeks the chart makes room for: 15. */
  pastWeeks: number
  /** Next week's forecast: expected count and range. */
  next: ModelForecast
  /** Next week's epidemic threshold, drawn as a line. */
  threshold: number
  /** The range's name in words, e.g. "90%". */
  rangeName: string
}

/** The city panel's chart. */
export default function WeeklyCasesChart({ past, pastWeeks, next, threshold, rangeName }: WeeklyCasesChartProps) {
  const slots = Array.from({ length: pastWeeks + 1 }, (_, slot) => slot)
  const x = scaleBand<number>().domain(slots).range([0, WIDTH]).paddingInner(0.4).paddingOuter(0.2)
  // A simulated week still under way has no count, so no bar
  const counts = past.flatMap((week) => (week.y === null ? [] : [week.y]))
  const tallest = Math.max(1, threshold, next.high, next.mu, ...counts)
  const y = scaleLinear().domain([0, tallest]).nice(5).range([HEIGHT, 0])
  const firstSlot = pastWeeks - past.length // The bars end just before next week's slot
  const middle = (x(pastWeeks) ?? 0) + x.bandwidth() / 2

  const label =
    (counts.length ? `Weekly cases over the last ${counts.length} weeks, from ${Math.min(...counts)} to ` +
      `${Math.max(...counts)}. ` : '') +
    `Next week: ${Math.round(next.mu)} expected, ${rangeName} range ${next.low} to ${next.high}. ` +
    `Epidemic threshold: ${Math.floor(threshold)} cases.` +
    (past.some((week) => week.simulated) ? ' Outlined bars are simulated counts.' : '')

  const weeksLabel = pastLabel(past.length)
  return (
    <figure className="weekly-cases-chart">
      <div className="weekly-cases-chart-area">
        <svg className="weekly-cases-chart-plot" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={label}>
          {past.map(
            (week, i) =>
              week.y !== null && (
                <rect
                  key={week.week_index}
                  // A simulated count is outlined, not filled
                  className={week.simulated ? 'weekly-cases-chart-bar weekly-cases-chart-bar-simulated' : 'weekly-cases-chart-bar'}
                  x={x(firstSlot + i)}
                  y={y(week.y)}
                  width={x.bandwidth()}
                  height={HEIGHT - y(week.y)}
                />
              ),
          )}
          <rect
            className="weekly-cases-chart-range"
            x={middle - MARK / 2}
            y={y(next.high)}
            width={MARK}
            height={y(next.low) - y(next.high)}
          />
          <rect
            className="weekly-cases-chart-forecast"
            x={middle - MARK / 2}
            y={y(next.mu) - MARK / 2}
            width={MARK}
            height={MARK}
          />
          <rect className="weekly-cases-chart-threshold" x={0} y={y(threshold)} width={WIDTH} height={1} />
        </svg>
        {/* The threshold's count at the line's right end (the panel's Epidemic threshold row) */}
        <span
          className="weekly-cases-chart-threshold-label label-ui-s"
          style={{ top: `${(y(threshold) / HEIGHT) * 100}%` }}
          aria-hidden="true"
        >
          {Math.floor(threshold)}
        </span>
      </div>
      {/* The two ends of the bars: the past weeks on the left, next week on the right */}
      <figcaption className="weekly-cases-chart-caption label-ui-s">
        {weeksLabel && <span>{weeksLabel}</span>}
        <span className="weekly-cases-chart-next">Next week</span>
      </figcaption>
    </figure>
  )
}
