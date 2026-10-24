import type { Map as MapLibreMap } from 'maplibre-gl'
import { BASE_SOURCE, ELEVATION_SOURCE } from './basemap.ts'
import { SLOTS } from './layerOrder.ts'
import { tokenColor } from './tokens.ts'

/* The 3D view, from the Layers panel's switch (?view=3d). */

/** How far the camera tilts in 3D, in degrees from looking straight down (MapLibre's most is 60). */
export const TILT = 60

/** How much the ground's heights are stretched. */
const EXAGGERATION = 2

/** The 3D view's own elevation source (the hill shading keeps its own, basemap.ts). */
const DEM = 'elevation-terrain'

/** The street map's buildings, raised to their height, from this zoom in. */
const BUILDINGS = 'buildings-3d'
const BUILDINGS_ZOOM = 14

/** How opaque the buildings are: the city, barangay and flood colors under them show through. */
const BUILDINGS_OPACITY = 0.7

/** The buildings, in the raised surface color (bg/raised); MapLibre shades their sides. */
function addBuildings(map: MapLibreMap) {
  const color = tokenColor(map.getContainer(), 'bg-raised')
  map.addLayer(
    {
      id: BUILDINGS,
      type: 'fill-extrusion',
      source: BASE_SOURCE,
      'source-layer': 'building',
      minzoom: BUILDINGS_ZOOM,
      paint: {
        'fill-extrusion-color': color,
        'fill-extrusion-height': ['get', 'render_height'],
        'fill-extrusion-base': ['get', 'render_min_height'],
        'fill-extrusion-opacity': BUILDINGS_OPACITY,
      },
    },
    SLOTS.buildings,
  )
}

/** Turns the 3D view on or off. */
export function set3D(map: MapLibreMap, on: boolean) {
  if (on && !map.getSource(DEM)) {
    map.addSource(DEM, ELEVATION_SOURCE)
  }
  if (on && !map.getLayer(BUILDINGS) && map.getSource(BASE_SOURCE)) {
    addBuildings(map)
  }
  map.setTerrain(on ? { source: DEM, exaggeration: EXAGGERATION } : null)
  if (map.getLayer(BUILDINGS)) {
    map.setLayoutProperty(BUILDINGS, 'visibility', on ? 'visible' : 'none')
  }
  if (on) {
    map.dragRotate.enable()
    map.touchPitch.enable()
    map.touchZoomRotate.enableRotation()
    map.keyboard.enableRotation()
  } else {
    map.dragRotate.disable()
    map.touchPitch.disable()
    map.touchZoomRotate.disableRotation()
    map.keyboard.disableRotation()
  }
}
