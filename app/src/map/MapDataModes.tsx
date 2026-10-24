import { dataNote } from './forecast.ts'
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

/** The map's two data modes, in its top right corner. Their sentence is in the info pop-up (MapInfo). */
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
      {/* Read out when the mode changes */}
      <p className="visually-hidden" aria-live="polite">
        {dataNote(shown, simulation, realEnd)}
      </p>
    </div>
  )
}
