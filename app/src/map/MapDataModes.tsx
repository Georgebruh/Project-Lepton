import { formatDay } from './forecast.ts'
import type { DataMode, Simulation } from './mapData.ts'
import './MapDataModes.css'

type MapDataModesProps = {
  mode: DataMode
  onMode: (mode: DataMode) => void
  /** The Simulation mode's file; null when it is missing, and then only Real data is offered. */
  simulation: Simulation | null
  /** The Saturday of the last week with a real count (city_forecast.json's last week). */
  realEnd: string
}

/**
 * F14: the map's two data modes, in its top right corner: a pair of buttons, Simulation | Real
 * data (the address keeps the choice, ?data=real). QCESD's counts stop weeks before today, so
 * Simulation shows LEPTON as it would run now: the real counts, made-up counts since (amber
 * "Simulated" badge on every one), and next week's forecast made with today's ECMWF rain forecast
 * (src/app_simulation.py). Real data shows QCESD's counts and B10's forecasts only. A line under
 * the buttons says what the mode shows.
 */
export default function MapDataModes({ mode, onMode, simulation, realEnd }: MapDataModesProps) {
  const shown = simulation ? mode : 'real'
  return (
    <div className="map-data-modes">
      <div className="map-data-modes-buttons" role="group" aria-label="Data">
        <button
          type="button"
          className="map-data-modes-button label-ui"
          aria-pressed={shown === 'simulation'}
          disabled={!simulation}
          onClick={() => onMode('simulation')}
        >
          Simulation
        </button>
        <button
          type="button"
          className="map-data-modes-button label-ui"
          aria-pressed={shown === 'real'}
          onClick={() => onMode('real')}
        >
          Real data
        </button>
      </div>
      <p className="map-data-modes-note body-s" aria-live="polite">
        {shown === 'simulation' && simulation
          ? `QCESD's counts to ${formatDay(simulation.last_real_week.end)}, then made up. This week's rain: ` +
            `ECMWF's forecast of ${formatDay(simulation.weather.fetched_on)}.`
          : `QCESD's counts and LEPTON's forecasts, to ${formatDay(realEnd)}.`}
      </p>
    </div>
  )
}
