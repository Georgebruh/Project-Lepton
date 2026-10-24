import { formatDay } from './forecast.ts'
import { WEATHER_LEGENDS, isLive, type Weather } from './weather.ts'
import './WeatherLegend.css'

type WeatherLegendProps = {
  kind: Weather
  /** The map's date (2024-10-22), which a layer of the map's date names. */
  day: string
}

/** The weather layer's legend. */
export default function WeatherLegend({ kind, day }: WeatherLegendProps) {
  const { title, stops, ends, credit } = WEATHER_LEGENDS[kind]
  const ramp = stops.map(([color, at]) => `${color} ${at}%`).join(', ')
  return (
    <div className="weather-legend">
      <p className="weather-legend-title label-ui-s">
        {title}
        {!isLive(kind) && ` · ${formatDay(day)}`}
      </p>
      {ends && (
        <>
          <span className="weather-legend-ramp" style={{ background: `linear-gradient(to right, ${ramp})` }} />
          <p className="weather-legend-ends body-s">
            <span>{ends[0]}</span>
            <span>{ends[1]}</span>
          </p>
        </>
      )}
      <p className="weather-legend-credit body-s">{credit}</p>
    </div>
  )
}
