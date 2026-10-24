import type {
  FilterSpecification,
  LayerSpecification,
  LineLayerSpecification,
  RasterDEMSourceSpecification,
  StyleSpecification,
} from '@maplibre/maplibre-gl-style-spec'
import type { MultiPolygon } from 'geojson'
import type { Map as MapLibreMap } from 'maplibre-gl'
import { shapeParts } from '../exposed/nearest.ts'
import { ISLANDS_ZOOM, fadeIn } from './borders.ts'
import { SLOTS } from './layerOrder.ts'
import type { Cities } from './mapData.ts'
import { tokenColor } from './tokens.ts'

/* The street map under LEPTON's data, OpenFreeMap's "Positron" style. */

/** The base maps the Layers panel offers, the street map first (the address leaves it out). */
export const BASE_MAPS = ['map', 'satellite', 'terrain'] as const
export type BaseMap = (typeof BASE_MAPS)[number]

/** How opaque LEPTON's fills are on each base map: over imagery or shading they let it show through. */
export const DATA_OPACITY: Record<BaseMap, number> = { map: 1, terrain: 0.75, satellite: 0.6 }

/** Satellite imagery: EOX's Sentinel-2 cloudless mosaic of 2024 (CC BY-NC-SA 4.0), sharpest at zoom 14. */
const SATELLITE = 'satellite'
const SATELLITE_TILES = 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/{z}/{y}/{x}.jpg'

/** The satellite choice's picture in the Layers panel: the imagery's tile over Metro Manila at zoom 11. */
export const SATELLITE_PREVIEW = SATELLITE_TILES.replace('{z}/{y}/{x}', '11/940/1712')
const SATELLITE_CREDIT =
  '<a href="https://s2maps.eu" target="_blank" rel="noopener">Sentinel-2 cloudless 2024</a> by EOX ' +
  '(contains modified Copernicus Sentinel data 2024)'

/** Elevation for the hill shading and the 3D view (terrain.ts). */
export const ELEVATION_SOURCE: RasterDEMSourceSpecification = {
  type: 'raster-dem',
  tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
  tileSize: 256,
  maxzoom: 15,
  encoding: 'terrarium',
  attribution:
    'Elevation: <a href="https://github.com/tilezen/joerd/blob/master/docs/attribution.md" target="_blank" rel="noopener">Mapzen Terrain Tiles</a>',
}
const HILLSHADE = 'hillshade'
const ELEVATION = 'elevation-hillshade'

/** How strongly the hills are shaded, 0 to 1. */
const HILLSHADE_STRENGTH = 0.5

/** The street map's ground the satellite imagery replaces; its roads and names stay over the imagery. */
const GROUND_SOURCE_LAYERS = ['landcover', 'landuse', 'park', 'water', 'building', 'aeroway']

/** The sources' names, for the Layers panel's credits line (the map's own credits link them). */
export const CREDITS = {
  street: 'Street map © OpenStreetMap contributors, OpenFreeMap',
  satellite: 'Satellite: Sentinel-2 cloudless 2024 by EOX',
  terrain: 'Terrain and 3D: Mapzen Terrain Tiles',
}

/** Per map, the street map's ground layers the satellite imagery hides (shown before it hid them). */
const hiddenGround = new WeakMap<MapLibreMap, string[]>()

/** OpenFreeMap's Positron style (checked 2026-10-21: no key, open to other sites). */
const BASE_STYLE_URL = 'https://tiles.openfreemap.org/styles/positron'

/** How long the loader waits for the style before drawing the map without it, in ms. */
const BASE_STYLE_TIMEOUT_MS = 2000

/** The style's tile source. */
export const BASE_SOURCE = 'openmaptiles'
const BASE_ATTRIBUTION =
  '<a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a> ' +
  '<a href="https://www.openmaptiles.org/" target="_blank" rel="noopener">© OpenMapTiles</a> ' +
  'Data from <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>'

/** The base map's place names that LEPTON writes itself inside a city with data. */
const PLACE_NAME_LAYERS = ['label_city', 'label_city_capital', 'label_town']


/** Fetches the street map's style. */
export async function fetchBaseStyle(): Promise<StyleSpecification | null> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), BASE_STYLE_TIMEOUT_MS)
  try {
    const res = await fetch(BASE_STYLE_URL, { signal: controller.signal })
    if (!res.ok) {
      throw new Error(`${res.status} ${res.statusText}`)
    }
    const style = (await res.json()) as StyleSpecification
    if (style.version !== 8 || !Array.isArray(style.layers)) {
      throw new Error('not a MapLibre style')
    }
    return style
  } catch (error) {
    console.warn(`The street map did not load (${error}); the map draws on a plain background.`)
    return null
  } finally {
    clearTimeout(timer)
  }
}

/** The colors the base map is drawn in, from tokens.css. */
function mapColors(element: HTMLElement) {
  const color = (token: string) => tokenColor(element, token)
  return {
    land: color('map-land'),
    water: color('bg-inset'),
    road: color('map-boundary'),
    /** The hill shading's dark and light sides. */
    shadow: color('text-primary'),
    highlight: color('bg-surface'),
  }
}

type MapColors = ReturnType<typeof mapColors>

/** The outlines of the cities with data as one shape, to hide the base map's names inside it. */
function dataOutline(cities: Cities): MultiPolygon {
  const named = cities.features.filter(({ properties }) => properties.has_data)
  return { type: 'MultiPolygon', coordinates: named.flatMap(({ geometry }) => shapeParts(geometry)) }
}

function addSatellite(map: MapLibreMap) {
  map.addSource(SATELLITE, {
    type: 'raster',
    tiles: [SATELLITE_TILES],
    tileSize: 256,
    maxzoom: 14,
    attribution: SATELLITE_CREDIT,
  })
  map.addLayer({ id: SATELLITE, type: 'raster', source: SATELLITE }, SLOTS.base)
}

function addHillshade(map: MapLibreMap) {
  const colors = mapColors(map.getContainer())
  map.addSource(ELEVATION, ELEVATION_SOURCE)
  map.addLayer(
    {
      id: HILLSHADE,
      type: 'hillshade',
      source: ELEVATION,
      paint: {
        'hillshade-shadow-color': colors.shadow,
        'hillshade-accent-color': colors.shadow,
        'hillshade-highlight-color': colors.highlight,
        'hillshade-exaggeration': HILLSHADE_STRENGTH,
      },
    },
    SLOTS.base,
  )
}

function show(map: MapLibreMap, layer: string, visible: boolean) {
  if (map.getLayer(layer)) {
    map.setLayoutProperty(layer, 'visibility', visible ? 'visible' : 'none')
  }
}

/** The street map's ground layers that are showing now: the ones the satellite imagery hides. */
function groundShown(map: MapLibreMap): string[] {
  return map.getLayersOrder().filter((id) => {
    const layer = map.getLayer(id)
    return (
      layer?.type === 'fill' &&
      GROUND_SOURCE_LAYERS.includes(layer.sourceLayer ?? '') &&
      map.getLayoutProperty(id, 'visibility') !== 'none'
    )
  })
}

/** Shows the base map `base`. */
export function setBase(map: MapLibreMap, base: BaseMap, view3d: boolean) {
  const shaded = base === 'terrain' || (base === 'map' && view3d)
  if (base === 'satellite' && !map.getLayer(SATELLITE)) {
    addSatellite(map)
  }
  if (shaded && !map.getLayer(HILLSHADE)) {
    addHillshade(map)
  }
  show(map, SATELLITE, base === 'satellite')
  show(map, HILLSHADE, shaded)
  const hidden = hiddenGround.get(map)
  if (base === 'satellite' && !hidden) {
    const ground = groundShown(map)
    ground.forEach((id) => show(map, id, false))
    hiddenGround.set(map, ground)
  }
  if (base !== 'satellite' && hidden) {
    hidden.forEach((id) => show(map, id, true))
    hiddenGround.delete(map)
  }
}

/** A street map line (a road, a river) that would show on the country's view starts at ISLANDS_ZOOM. */
function fromIslandsZoom(layer: LineLayerSpecification): LineLayerSpecification {
  if ((layer.minzoom ?? 0) >= ISLANDS_ZOOM) {
    return layer
  }
  const opacity = layer.paint?.['line-opacity'] ?? 1
  const fade = typeof opacity === 'number' ? { 'line-opacity': fadeIn(ISLANDS_ZOOM, opacity) } : {}
  return { ...layer, minzoom: ISLANDS_ZOOM, paint: { ...layer.paint, ...fade } }
}

/** One base map layer in the app's colors. */
function adaptLayer(layer: LayerSpecification, colors: MapColors, named: MultiPolygon): LayerSpecification[] {
  if (layer.type === 'background') {
    return [{ ...layer, paint: { ...layer.paint, 'background-color': colors.land } }]
  }
  if (layer.type === 'fill' && layer['source-layer'] === 'water') {
    return [{ ...layer, paint: { ...layer.paint, 'fill-color': colors.water } }]
  }
  // The borders are LEPTON's own (borders.ts and CityMap)
  if (layer.type === 'line' && layer['source-layer'] === 'boundary') {
    return []
  }
  // Positron's roads are white on grey; on the app's lighter land they take the map's border color
  if (layer.type === 'line' && layer['source-layer'] === 'transportation' && !layer.id.endsWith('dashline')) {
    return [fromIslandsZoom({ ...layer, paint: { ...layer.paint, 'line-color': colors.road } })]
  }
  if (layer.type === 'line') {
    return [fromIslandsZoom(layer)]
  }
  if (layer.type === 'symbol' && PLACE_NAME_LAYERS.includes(layer.id)) {
    const outside = ['!', ['within', named]] as FilterSpecification
    return [{ ...layer, filter: (layer.filter ? ['all', layer.filter, outside] : outside) as FilterSpecification }]
  }
  return [layer]
}

/** The style CityMap makes the map with. */
export function mapStyle(base: StyleSpecification | null, element: HTMLElement, cities: Cities): StyleSpecification {
  const colors = mapColors(element)
  const flat: Pick<StyleSpecification, 'projection'> = { projection: { type: 'mercator' } }
  if (!base) {
    return {
      version: 8,
      sources: {},
      layers: [{ id: 'background', type: 'background', paint: { 'background-color': colors.water } }],
      ...flat,
    }
  }
  const named = dataOutline(cities)
  const sources = Object.fromEntries(
    Object.entries(base.sources).map(([id, source]) => [
      id,
      id === BASE_SOURCE ? { ...source, attribution: BASE_ATTRIBUTION } : source,
    ]),
  )
  return { ...base, sources, layers: base.layers.flatMap((layer) => adaptLayer(layer, colors, named)), ...flat }
}
