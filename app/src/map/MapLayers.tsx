import { useEffect, useRef, type KeyboardEvent } from 'react'
import Icon from '../components/Icon.tsx'
import { BASE_MAPS, CREDITS, SATELLITE_PREVIEW, type BaseMap } from './basemap.ts'
import './MapLayers.css'

/** Each base map's name in the panel, and what screen readers hear when it is chosen. */
const BASE_NAMES: Record<BaseMap, string> = { map: 'Map', satellite: 'Satellite', terrain: 'Terrain' }
const BASE_SHOWN: Record<BaseMap, string> = {
  map: 'Street map shown',
  satellite: 'Satellite imagery shown under the map',
  terrain: 'Terrain shading shown under the map',
}

type MapLayersProps = {
  /** The panel's id, which the Layers button names in its aria-controls. */
  id: string
  base: BaseMap
  onBase: (base: BaseMap) => void
  /** Whether the street map loaded (if not, the map shows a plain background and the panel does not credit it). */
  hasStreetMap: boolean
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
 */
export default function MapLayers({ id, base, onBase, hasStreetMap, onClose }: MapLayersProps) {
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
      <p className="map-layers-credits body-s">
        {[hasStreetMap && CREDITS.street, CREDITS.satellite, CREDITS.terrain].filter(Boolean).join(' · ')}
      </p>
      <p className="visually-hidden" aria-live="polite">
        {BASE_SHOWN[base]}
      </p>
    </section>
  )
}
