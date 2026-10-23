import type { CSSProperties } from 'react'
import Icon from '../components/Icon.tsx'
import DatePicker from './DatePicker.tsx'
import { addDays, formatDay, formatWeek, forecastFor, weekStart } from './forecast.ts'
import type { CityForecast } from './mapData.ts'
import './MapTimeline.css'

const DAY_MS = 24 * 60 * 60 * 1000

/** The weeks from the week holding `from` to the week holding `to`. */
function weeksBetween(from: string, to: string): number {
  return Math.round((Date.parse(weekStart(to)) - Date.parse(weekStart(from))) / (7 * DAY_MS))
}

type MapTimelineProps = {
  /** The chosen date, YYYY-MM-DD, and the first and last the map offers (forecast.ts, dateRange). */
  date: string
  first: string
  last: string
  /** The forecast the map shows, in its mode: its weeks name the target week and the simulated ones. */
  forecast: CityForecast
  onChange: (day: string) => void
}

/**
 * F14: the map's timeline, at the bottom in the middle of the map (it was F4's date picker in the
 * breadcrumb bar). Each step is a forecast week: the previous and next week's buttons, a slider
 * over every week the map has forecasts for, and the date picker for a day. Under it, the week
 * the forecast is for. In Simulation mode the slider's simulated weeks are tinted amber, so a
 * reader sees where QCESD's counts end. The slider is a native range input: the arrow keys move
 * it a week, and screen readers hear each date.
 */
export default function MapTimeline({ date, first, last, forecast, onChange }: MapTimelineProps) {
  const steps = Math.max(1, weeksBetween(first, last))
  const index = weeksBetween(first, date)
  const target = forecastFor(forecast, date)
  // The forecast week from which the counts behind the forecasts are made up (the first simulated target's week before)
  const firstSimulated = forecast.weeks.find((week) => week.simulated)
  const simulatedFrom = firstSimulated
    ? weeksBetween(first, addDays(firstSimulated.start, -7 * forecast.horizon_weeks)) / steps
    : 1
  const track = {
    '--map-timeline-played': `${(index / steps) * 100}%`,
    '--map-timeline-simulated': `${Math.min(1, Math.max(0, simulatedFrom)) * 100}%`,
  } as CSSProperties

  /** Moves the date by whole weeks, keeping its weekday, inside the dates the map offers. */
  function moveTo(step: number) {
    const day = addDays(date, 7 * (step - index))
    onChange(day < first ? first : day > last ? last : day)
  }

  return (
    <div className="map-timeline" role="group" aria-label="Forecast date">
      <button
        type="button"
        className="map-timeline-step"
        aria-label="Previous week"
        disabled={index <= 0}
        onClick={() => moveTo(index - 1)}
      >
        <Icon name="chevron-left" size={18} />
      </button>
      <div className="map-timeline-middle">
        <div className="map-timeline-when">
          <DatePicker value={date} min={first} max={last} onChange={onChange} />
          <span className="map-timeline-target body-s">
            {target ? `Forecast for ${formatWeek(target.start, target.end)}` : 'No forecast for the week after this date'}
          </span>
        </div>
        <input
          type="range"
          className="map-timeline-slider"
          style={track}
          min={0}
          max={steps}
          value={index}
          aria-label="Forecast week"
          aria-valuetext={formatDay(date)}
          onChange={(event) => moveTo(Number(event.target.value))}
        />
      </div>
      <button
        type="button"
        className="map-timeline-step"
        aria-label="Next week"
        disabled={index >= steps}
        onClick={() => moveTo(index + 1)}
      >
        <Icon name="chevron-right" size={18} />
      </button>
    </div>
  )
}
