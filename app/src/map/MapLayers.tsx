import { useEffect, useRef, type KeyboardEvent } from 'react'
import Icon from '../components/Icon.tsx'
import ToggleRow from '../components/ToggleRow.tsx'
import { BASE_MAPS, CREDITS, SATELLITE_PREVIEW, type BaseMap } from './basemap.ts'
import { FLOOD_PERIODS, type FloodPeriod, type FloodStatus } from './floodLayer.ts'
import { formatDay } from './forecast.ts'
import { WEATHER, WEATHER_CREDIT, WEATHER_NAMES, isLive, type Weather, type WeatherStatus } from './weather.ts'
import './MapLayers.css'

/** Each base map's name in the panel, and what screen readers hear when it is chosen. */
const BASE_NAMES: Record<BaseMap, string> = { map: 'Map', satellite: 'Satellite', terrain: 'Terrain' }
const BASE_SHOWN: Record<BaseMap, string> = {
  map: 'Street map shown',
  satellite: 'Satellite imagery shown under the map',
  terrain: 'Terrain shading shown under the map',
}

/** What screen readers hear of the weather layer `kind` as it loads. */
function weatherWords(status: WeatherStatus, kind: Weather | null, day: string): string {
  if (status === 'off' || kind === null) {
    return 'Weather off'
  }
  const { label, picture } = WEATHER_NAMES[kind]
  return {
    loading: `Loading ${picture}`,
    shown: `${label} shown`,
    missing: isLive(kind) ? `No frames of ${picture} right now` : `No picture from NASA for ${formatDay(day)}`,
    failed: `Couldn't load ${picture}`,
  }[status]
}

/** What screen readers hear when the 3D view is turned on or off. */
const VIEW_WORDS = {
  on: 'Map tilted in 3D: drag with the right mouse button, two fingers, or Shift and the arrow keys to turn and tilt it',
  off: 'Map flat, facing north',
}

/** What screen readers hear of NOAH's map `period` as it loads, shows or fails; `city`: only its zones. */
function floodWords(status: FloodStatus, period: FloodPeriod | null, city: string | null): string {
  if (status === 'off' || period === null) {
    return 'Flood zones hidden'
  }
  const map = `NOAH's ${period}-year map`
  const shown = city ? `${map} of flood zones shown in ${city} only` : `${map} of flood zones shown`
  return { loading: `Loading ${map}`, shown, failed: `Couldn't load ${map}` }[status]
}

type MapLayersProps = {
  /** The panel's id, which the Layers button names in its aria-controls. */
  id: string
  base: BaseMap
  onBase: (base: BaseMap) => void
  /** Whether the map is in 3D: tilted, with the ground's relief and buildings (terrain.ts). */
  view3d: boolean
  on3D: (on: boolean) => void
  /** Whether the street map loaded. */
  hasStreetMap: boolean
  /** The NOAH map of flood zones shown, by its rain's return period; null when they are off. */
  flood: FloodPeriod | null
  /** The map the flood switch shows when turned on: the one last picked. */
  floodChoice: FloodPeriod
  /** How the NOAH map shown is doing (floodLayer.ts). */
  floodStatus: FloodStatus
  /** The city whose zones alone are shown while it is open or found; null: every zone. */
  floodCity: string | null
  onFlood: (period: FloodPeriod | null) => void
  /** Fetches a map that failed to load again. */
  onFloodRetry: () => void
  /** The weather layer shown (weather.ts); null when none is. */
  weather: Weather | null
  /** How the weather layer is doing. */
  weatherStatus: WeatherStatus
  /** The map's date, which the weather layers of the map's date show. */
  day: string
  onWeather: (kind: Weather | null) => void
  /** Fetches a weather layer that failed to load again. */
  onWeatherRetry: () => void
  /** Closes the panel; the layout then gives the keyboard back to the Layers button. */
  onClose: () => void
}

/** The map's Layers panel, opened by the Layers button above Zoom. */
export default function MapLayers({
  id,
  base,
  onBase,
  view3d,
  on3D,
  hasStreetMap,
  flood,
  floodChoice,
  floodStatus,
  floodCity,
  onFlood,
  onFloodRetry,
  weather,
  weatherStatus,
  day,
  onWeather,
  onWeatherRetry,
  onClose,
}: MapLayersProps) {
  const chosen = useRef<HTMLInputElement>(null)

  // Opening the panel moves the keyboard to the base map shown
  useEffect(() => {
    chosen.current?.focus()
  }, [])

  function onKeyDown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      event.stopPropagation()
      onClose()
    }
  }

  return (
    <section id={id} className="map-layers" aria-labelledby={`${id}-title`} onKeyDown={onKeyDown}>
      <div className="map-layers-header">
        <h2 id={`${id}-title`} className="heading-s">
          Map layers
        </h2>
        <button type="button" className="map-layers-close" aria-label="Close map layers" onClick={onClose}>
          <Icon name="close" size={20} />
        </button>
      </div>
      <fieldset className="map-layers-section">
        <legend className="map-layers-title label-ui-s">Base map</legend>
        <div className="map-layers-bases">
          {BASE_MAPS.map((option) => (
            <label key={option} className="map-layers-base">
              <input
                ref={option === base ? chosen : undefined}
                type="radio"
                name={`${id}-base`}
                className="visually-hidden"
                value={option}
                checked={option === base}
                onChange={() => onBase(option)}
              />
              <span className={`map-layers-preview map-layers-preview-${option}`} aria-hidden="true">
                {option === 'satellite' && <img src={SATELLITE_PREVIEW} alt="" loading="lazy" />}
              </span>
              <span className="label-ui-s">{BASE_NAMES[option]}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <ToggleRow label="3D view: tilt, terrain, buildings" on={view3d} onChange={on3D} />
      <fieldset className="map-layers-section">
        <legend className="map-layers-title label-ui-s">Flood hazard</legend>
        <div className="map-layers-flood">
          <ToggleRow label="NOAH flood zones" on={flood !== null} onChange={(on) => onFlood(on ? floodChoice : null)} />
          {flood !== null && (
            <>
              <div
                className="map-layers-chips"
                role="group"
                aria-label="NOAH map"
                aria-describedby={`${id}-flood-about`}
              >
                {FLOOD_PERIODS.map((period) => (
                  <button
                    key={period}
                    type="button"
                    className="map-layers-chip label-ui-s"
                    aria-pressed={period === flood}
                    onClick={() => onFlood(period)}
                  >
                    {period}-year
                  </button>
                ))}
              </div>
              <p id={`${id}-flood-about`} className="map-layers-about body-s">
                A flood from rain that comes once in 5, 25 or 100 years on average.
              </p>
              {floodStatus === 'loading' && <p className="map-layers-about body-s">Loading NOAH's {flood}-year map…</p>}
              {floodStatus === 'failed' && (
                <p className="map-layers-failed body-s">
                  Couldn't load NOAH's {flood}-year map; the rest of the map works as before.{' '}
                  <button type="button" className="map-layers-retry body-s" onClick={onFloodRetry}>
                    Try again
                  </button>
                </p>
              )}
            </>
          )}
        </div>
      </fieldset>
      <fieldset className="map-layers-section">
        <legend className="map-layers-title label-ui-s">Weather · one at a time</legend>
        {[null, ...WEATHER].map((option) => (
          <label key={option ?? 'off'} className="map-layers-radio">
            <input
              type="radio"
              name={`${id}-weather`}
              className="map-layers-radio-input"
              value={option ?? 'off'}
              checked={option === weather}
              onChange={() => onWeather(option)}
            />
            <span className="map-layers-radio-text">
              <span className="body-m">{option ? WEATHER_NAMES[option].label : 'Off'}</span>
              {option && <span className="map-layers-radio-caption body-s">{WEATHER_NAMES[option].caption}</span>}
            </span>
          </label>
        ))}
        {weather && weatherStatus === 'loading' && (
          <p className="map-layers-about body-s">Loading {WEATHER_NAMES[weather].picture}…</p>
        )}
        {weather && weatherStatus === 'missing' && (
          <p className="map-layers-about body-s">
            {isLive(weather)
              ? `No frames of ${WEATHER_NAMES[weather].picture} right now.`
              : `No picture from NASA for ${formatDay(day)}.`}
          </p>
        )}
        {weather && weatherStatus === 'failed' && (
          <p className="map-layers-failed body-s">
            Couldn't load {WEATHER_NAMES[weather].picture}; the rest of the map works as before.{' '}
            <button type="button" className="map-layers-retry body-s" onClick={onWeatherRetry}>
              Try again
            </button>
          </p>
        )}
      </fieldset>
      <p className="map-layers-credits body-s">
        {[hasStreetMap && CREDITS.street, CREDITS.satellite, CREDITS.terrain, WEATHER_CREDIT]
          .filter(Boolean)
          .join(' · ')}
      </p>
      {/* One line for all four, in parts: only the part that changed is read out */}
      <p className="visually-hidden" aria-live="polite">
        <span>{BASE_SHOWN[base]}. </span>
        <span>{VIEW_WORDS[view3d ? 'on' : 'off']}. </span>
        <span>{floodWords(floodStatus, flood, floodCity)}. </span>
        <span>{weatherWords(weatherStatus, weather, day)}.</span>
      </p>
    </section>
  )
}
