import type { Map as MapLibreMap } from 'maplibre-gl'
import { BASE_SOURCE, ELEVATION_SOURCE } from './basemap.ts'
import { SLOTS } from './layerOrder.ts'

/*
 * F13: the 3D view, from the Layers panel's switch (?view=3d). The ground rises with its
 * elevation (Mapzen's Terrain Tiles, as for the terrain base map's shading, from a source of its
 * own), the street map's buildings stand up from zoom 14 (OpenStreetMap's heights), and the
 * reader may turn and tilt the map: a right-button drag with a mouse, two fingers on a touch
 * screen, or Shift and the arrow keys. CityMap tilts the camera (TILT); everything LEPTON draws
 * lies on the ground, and the names' boxes follow it.
 */

/** How far the camera tilts in 3D, in degrees from looking straight down (MapLibre's most is 60). */
export const TILT = 60

/**
 * How much the ground's heights are stretched. Metro Manila is low: Quezon City rises from a few
 * metres by the rivers to about 250 m, so at true height the relief would barely show.
 */
const EXAGGERATION = 2

/** The 3D view's own elevation source (the hill shading keeps its own, basemap.ts). */
const DEM = 'elevation-terrain'

/** The street map's buildings, raised to their height, from this zoom in (closer to a street than a city). */
const BUILDINGS = 'buildings-3d'
const BUILDINGS_ZOOM = 14

/** How opaque the buildings are: the city, barangay and flood colors under them show through. */
const BUILDINGS_OPACITY = 0.7

/** The buildings, in the raised surface color (bg/raised), read from tokens.css; MapLibre shades their sides. */
function addBuildings(map: MapLibreMap) {
  const color = getComputedStyle(map.getContainer()).getPropertyValue('--color-bg-raised').trim()
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

/**
 * Turns the 3D view on or off: the ground's relief, the buildings (only with the street map,
 * which has them), and turning and tilting by mouse, touch and keyboard. The camera is CityMap's.
 */
export function set3D(map: MapLibreMap, on: boolean) {
  if (on && !map.getSource(DEM)) {
    map.addSource(DEM, ELEVATION_SOURCE)
  }
  if (on && !map.getLayer(BUILDINGS) && map.getSource(BASE_SOURCE)) {
    addBuildings(map)
  }
  // MapLibre does not fully support raised ground on the globe (zoomed out, tiles went missing in
  // tests), so the 3D view lays the world flat; at a city's size the two look the same
  map.setProjection({ type: on ? 'mercator' : 'globe' })
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
