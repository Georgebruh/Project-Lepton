import { useEffect, useRef, type KeyboardEvent } from 'react'
import Icon from '../components/Icon.tsx'
import ToggleRow from '../components/ToggleRow.tsx'
import { BASE_MAPS, CREDITS, SATELLITE_PREVIEW, type BaseMap } from './basemap.ts'
import { FLOOD_PERIODS, type FloodPeriod, type FloodStatus } from './floodLayer.ts'
import './MapLayers.css'

/** Each base map's name in the panel, and what screen readers hear when it is chosen. */
const BASE_NAMES: Record<BaseMap, string> = { map: 'Map', satellite: 'Satellite', terrain: 'Terrain' }
const BASE_SHOWN: Record<BaseMap, string> = {
  map: 'Street map shown',
  satellite: 'Satellite imagery shown under the map',
  terrain: 'Terrain shading shown under the map',
}

/** What screen readers hear when the 3D view is turned on or off. */
const VIEW_WORDS = {
  on: 'Map tilted in 3D: drag with the right mouse button, two fingers, or Shift and the arrow keys to turn and tilt it',
  off: 'Map flat, facing north',
}

/** What screen readers hear of NOAH's map `period` as it loads, shows or fails; and when the zones are turned off. */
function floodWords(status: FloodStatus, period: FloodPeriod | null): string {
  if (status === 'off' || period === null) {
    return 'Flood zones hidden'
  }
  const map = `NOAH's ${period}-year map`
  return { loading: `Loading ${map}`, shown: `${map} of flood zones shown`, failed: `Couldn't load ${map}` }[status]
}

type MapLayersProps = {
  /** The panel's id, which the Layers button names in its aria-controls. */
  id: string
  base: BaseMap
  onBase: (base: BaseMap) => void
  /** Whether the map is in 3D: tilted, with the ground's relief and buildings (terrain.ts). */
  view3d: boolean
  on3D: (on: boolean) => void
  /** Whether the street map loaded (if not, the map shows a plain background and the panel does not credit it). */
  hasStreetMap: boolean
  /** The NOAH map of flood zones shown, by its rain's return period; null when they are off. */
  flood: FloodPeriod | null
  /** The map the flood switch shows when turned on: the one last picked. */
  floodChoice: FloodPeriod
  /** How the NOAH map shown is doing (floodLayer.ts). */
  floodStatus: FloodStatus
  onFlood: (period: FloodPeriod | null) => void
  /** Fetches a map that failed to load again. */
  onFloodRetry: () => void
  /** Closes the panel; the layout then gives the keyboard back to the Layers button. */
  onClose: () => void
}

/**
 * F13: the map's Layers panel, Figma "Layers panel" (Components page) and frame "Map · L1
 * Layers open", opened by the Layers button above Zoom. It opens up from the button and covers
 * the legends while open; on a phone it is a sheet over the map's lower part (MapLayers.css).
 * Close or Escape closes it.
 *
 * The base maps are a group of radio buttons drawn as Figma's "Base map option" cards, so the
 * arrow keys move between them; the satellite's picture is a tile of its imagery, the other two
 * are drawn with the map's tokens (MapLayers.css). The choice lives in the address (?base=,
 * layerParams.ts), and a line read out by screen readers says what the map now shows.
 *
 * The 3D view: a switch that tilts the map over the ground's relief, with buildings (?view=3d).
 *
 * Flood hazard: a switch for NOAH's flood zones (floodLayer.ts) and, while they are on, the
 * chips that pick NOAH's map for a 5-, 25- or 100-year rain (?flood=), like the plan's lead
 * chips. While a map loads, or if it fails, a line under the chips says so; a failed map has
 * a Try again button.
 */
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
  onFlood,
  onFloodRetry,
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
      <p className="map-layers-credits body-s">
        {[hasStreetMap && CREDITS.street, CREDITS.satellite, CREDITS.terrain].filter(Boolean).join(' · ')}
      </p>
      {/* One line for all three, in parts: only the part that changed is read out */}
      <p className="visually-hidden" aria-live="polite">
        <span>{BASE_SHOWN[base]}. </span>
        <span>{VIEW_WORDS[view3d ? 'on' : 'off']}. </span>
        <span>{floodWords(floodStatus, flood)}.</span>
      </p>
    </section>
  )
}
