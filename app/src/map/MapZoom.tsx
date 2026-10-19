import type { Map as MapLibreMap } from 'maplibre-gl'
import Icon from '../components/Icon.tsx'
import './MapZoom.css'

type MapZoomProps = {
  /** The map to zoom; null until it has been created. */
  map: MapLibreMap | null
}

/**
 * F4: the map's zoom buttons, Figma "Zoom" (node 55:364). MapLibre's own zoom animation
 * follows the reader's reduced-motion setting.
 */
export default function MapZoom({ map }: MapZoomProps) {
  return (
    <div className="map-zoom" role="group" aria-label="Zoom">
      <button type="button" className="map-zoom-button" aria-label="Zoom in" onClick={() => map?.zoomIn()}>
        <Icon name="plus" size={18} />
      </button>
      <button type="button" className="map-zoom-button" aria-label="Zoom out" onClick={() => map?.zoomOut()}>
        <Icon name="minus" size={18} />
      </button>
    </div>
  )
}
