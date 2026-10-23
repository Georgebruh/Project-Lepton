import type {
  FilterSpecification,
  LayerSpecification,
  RasterDEMSourceSpecification,
  StyleSpecification,
} from '@maplibre/maplibre-gl-style-spec'
import type { MultiPolygon } from 'geojson'
import type { Map as MapLibreMap } from 'maplibre-gl'
import { shapeParts } from '../exposed/nearest.ts'
import { SLOTS } from './layerOrder.ts'
import type { Cities } from './mapData.ts'
import { tokenColor } from './tokens.ts'

/*
 * F13: the street map under LEPTON's data, OpenFreeMap's "Positron" style: OpenStreetMap data
 * in the OpenMapTiles schema, free and with no key. The /map route's loader fetches the style
 * once (fetchBaseStyle); CityMap adapts it to the app before making the map (mapStyle):
 *   - land, water and roads take the Figma map colors (map/land, bg/inset, map/boundary);
 *   - the base map's own city and town names inside a city with data (Quezon City) are hidden,
 *     since LEPTON writes its name itself, in Figtree, with next week's cases. F14: at every
 *     zoom, so a reader finds the one city with data on the map of the whole country (F13 hid
 *     LEPTON's 17 NCR names zoomed out, where they piled up); everywhere else the base map
 *     names the Philippines' cities and towns;
 *   - the flat (Mercator) map of the whole world: zoomed out, it shows every continent. A globe
 *     looked better zoomed out but cost a freeze: MapLibre compiles each of its shaders twice
 *     for a globe (once round, once flat for close up), and on an integrated GPU each compile
 *     holds the page up to a third of a second (measured 22 October 2026: 31 shaders and 1.6 s
 *     frozen at the plan level, against 10 and 0.3 s before F13).
 * If the style cannot be fetched, the map draws on the plain background it had before F13, so
 * LEPTON's data always shows.
 *
 * The Layers panel offers three base maps (setBase): the street map; satellite imagery
 * (Sentinel-2 cloudless 2024 by EOX, 10 m pixels), with the street map's roads and names kept
 * over it; and terrain, the street map with hill shading from elevation tiles (Mapzen Terrain
 * Tiles on AWS). Each is added the first time it is chosen, in the base slot (layerOrder.ts).
 * In the 3D view the street map gets the hill shading too: MapLibre does not light the ground
 * it raises, so without shading the relief would show only at its edges.
 */

/** The base maps the Layers panel offers, the street map first (the address leaves it out). */
export const BASE_MAPS = ['map', 'satellite', 'terrain'] as const
export type BaseMap = (typeof BASE_MAPS)[number]

/** How opaque LEPTON's fills are on each base map: over imagery or shading they let it show through (Figma notes). */
export const DATA_OPACITY: Record<BaseMap, number> = { map: 1, terrain: 0.75, satellite: 0.6 }

/** Satellite imagery: EOX's Sentinel-2 cloudless mosaic of 2024 (CC BY-NC-SA 4.0), sharpest at zoom 14. */
const SATELLITE = 'satellite'
const SATELLITE_TILES = 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/{z}/{y}/{x}.jpg'

/** The satellite choice's picture in the Layers panel: the imagery's tile over Metro Manila at zoom 11. */
export const SATELLITE_PREVIEW = SATELLITE_TILES.replace('{z}/{y}/{x}', '11/940/1712')
const SATELLITE_CREDIT =
  '<a href="https://s2maps.eu" target="_blank" rel="noopener">Sentinel-2 cloudless 2024</a> by EOX ' +
  '(contains modified Copernicus Sentinel data 2024)'

/**
 * Elevation for the hill shading and the 3D view (terrain.ts): Mapzen's Terrain Tiles on AWS
 * (terrarium encoding, SRTM in the Philippines). Each makes its own source from it, as MapLibre
 * advises for hill shading and terrain.
 */
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

/** How strongly the hills are shaded, 0 to 1: Metro Manila is low, but Marikina's valley and the Sierra Madre's foothills show. */
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

/**
 * How long the loader waits for the style before drawing the map without it, in ms. The map
 * waits for the style, so this is the most a slow or blocked street map can delay LEPTON's
 * data; the style is small and cached for a day, so it usually comes in well under a second.
 */
const BASE_STYLE_TIMEOUT_MS = 2000

/** The style's tile source (terrain.ts raises its buildings), and the credit its tiles need (OpenFreeMap's style leaves it empty). */
export const BASE_SOURCE = 'openmaptiles'
const BASE_ATTRIBUTION =
  '<a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a> ' +
  '<a href="https://www.openmaptiles.org/" target="_blank" rel="noopener">© OpenMapTiles</a> ' +
  'Data from <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>'

/** The base map's place names that LEPTON writes itself inside a city with data. */
const PLACE_NAME_LAYERS = ['label_city', 'label_city_capital', 'label_town']


/** Fetches the street map's style; null if it does not come within BASE_STYLE_TIMEOUT_MS or is not a style. */
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

/**
 * Shows the base map `base`: the street map alone, the satellite imagery under the street map's
 * roads and names (its ground hidden), or the street map with hill shading. Leaving the imagery
 * shows again exactly the ground it hid. In the 3D view (`view3d`) the street map is shaded too.
 */
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

/** One base map layer in the app's colors; a layer of names LEPTON writes itself, without those inside the cities with data. */
function adaptLayer(layer: LayerSpecification, colors: MapColors, named: MultiPolygon): LayerSpecification[] {
  if (layer.type === 'background') {
    return [{ ...layer, paint: { ...layer.paint, 'background-color': colors.land } }]
  }
  if (layer.type === 'fill' && layer['source-layer'] === 'water') {
    return [{ ...layer, paint: { ...layer.paint, 'fill-color': colors.water } }]
  }
  // Positron's roads are white on grey; on the app's lighter land they take the map's border color
  if (layer.type === 'line' && layer['source-layer'] === 'transportation' && !layer.id.endsWith('dashline')) {
    return [{ ...layer, paint: { ...layer.paint, 'line-color': colors.road } }]
  }
  if (layer.type === 'symbol' && PLACE_NAME_LAYERS.includes(layer.id)) {
    const outside = ['!', ['within', named]] as FilterSpecification
    return [{ ...layer, filter: (layer.filter ? ['all', layer.filter, outside] : outside) as FilterSpecification }]
  }
  return [layer]
}

/**
 * The style CityMap makes the map with: the street map adapted to the app, or, without one,
 * the plain background the map had before F13 (bg/inset). Both are flat (Mercator) maps.
 * `element` is the map's element, for the token colors.
 */
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
