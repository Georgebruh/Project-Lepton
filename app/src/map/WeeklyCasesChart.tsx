import { scaleBand, scaleLinear } from 'd3-scale'
import type { ForecastWeek, ModelForecast } from './mapData.ts'
import './WeeklyCasesChart.css'

/** The plot's size in px, from Figma "Weekly cases" (node 53:345): 351 wide, bars standing on a line 130 down. */
const WIDTH = 351
const HEIGHT = 130
/** Next week's marks are 10 px wide: the range as a bar, the expected count as a square. */
const MARK = 10

/** The caption, counting the weeks drawn: "Last 15 weeks · next week"; fewer at the backtest's start. */
function caption(weeks: number): string {
  if (weeks === 0) {
    return 'Next week'
  }
  return `${weeks === 1 ? 'Last week' : `Last ${weeks} weeks`} · next week`
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

/**
 * F4: the city panel's chart, Figma "Weekly cases" (node 53:345): the last 15 weeks' counts as
 * grey bars, then next week's forecast, its range as a pale teal bar and its expected count as a
 * teal square, and the epidemic threshold as an amber line across.
 *
 * The weeks stand in 16 equal slots, each bar 60% of its slot (d3's band scale, padding 0.4
 * between and 0.2 at the ends). Counts run from 0 at the bottom to a round number above the
 * tallest mark (d3's nice(), about 5 steps): in Figma 88 cases is the tallest, so the top is 100.
 */
export default function WeeklyCasesChart({ past, pastWeeks, next, threshold, rangeName }: WeeklyCasesChartProps) {
  const slots = Array.from({ length: pastWeeks + 1 }, (_, slot) => slot)
  const x = scaleBand<number>().domain(slots).range([0, WIDTH]).paddingInner(0.4).paddingOuter(0.2)
  const tallest = Math.max(1, threshold, next.high, next.mu, ...past.map((week) => week.y))
  const y = scaleLinear().domain([0, tallest]).nice(5).range([HEIGHT, 0])
  const firstSlot = pastWeeks - past.length // the bars end just before next week's slot
  const middle = (x(pastWeeks) ?? 0) + x.bandwidth() / 2

  const counts = past.map((week) => week.y)
  const label =
    (counts.length ? `Weekly cases over the last ${counts.length} weeks, from ${Math.min(...counts)} to ` +
      `${Math.max(...counts)}. ` : '') +
    `Next week: ${Math.round(next.mu)} expected, ${rangeName} range ${next.low} to ${next.high}. ` +
    `Epidemic threshold: ${Math.floor(threshold)} cases.`

  return (
    <figure className="weekly-cases-chart">
      <svg className="weekly-cases-chart-plot" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={label}>
        {past.map((week, i) => (
          <rect
            key={week.week_index}
            className="weekly-cases-chart-bar"
            x={x(firstSlot + i)}
            y={y(week.y)}
            width={x.bandwidth()}
            height={HEIGHT - y(week.y)}
          />
        ))}
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
      <figcaption className="weekly-cases-chart-caption label-ui-s">{caption(past.length)}</figcaption>
    </figure>
  )
}
