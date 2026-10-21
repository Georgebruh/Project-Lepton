import type {
  FilterSpecification,
  LayerSpecification,
  SkySpecification,
  StyleSpecification,
} from '@maplibre/maplibre-gl-style-spec'
import type { MultiPolygon } from 'geojson'
import { shapeParts } from '../exposed/nearest.ts'
import type { Cities } from './mapData.ts'

/*
 * F13: the street map under LEPTON's data, OpenFreeMap's "Positron" style: OpenStreetMap data
 * in the OpenMapTiles schema, free and with no key. The /map route's loader fetches the style
 * once (fetchBaseStyle); CityMap adapts it to the app before making the map (mapStyle):
 *   - land, water and roads take the Figma map colors (map/land, bg/inset, map/boundary);
 *   - the base map's own city and town names inside NCR are hidden where LEPTON writes the
 *     cities' names itself (from CITY_NAMES_ZOOM in), in Figtree, with next week's cases;
 *     zoomed further out, LEPTON's names hide and the base map's come back;
 *   - the globe projection: zoomed out, the map is the whole Earth.
 * If the style cannot be fetched, the map draws on the plain background it had before F13, so
 * LEPTON's data always shows.
 */

/** OpenFreeMap's Positron style (checked 2026-10-21: no key, open to other sites). */
const BASE_STYLE_URL = 'https://tiles.openfreemap.org/styles/positron'

/**
 * How long the loader waits for the style before drawing the map without it, in ms. The map
 * waits for the style, so this is the most a slow or blocked street map can delay LEPTON's
 * data; the style is small and cached for a day, so it usually comes in well under a second.
 */
const BASE_STYLE_TIMEOUT_MS = 2000

/** The style's tile source, and the credit its tiles need (OpenFreeMap's style leaves it empty). */
const BASE_SOURCE = 'openmaptiles'
const BASE_ATTRIBUTION =
  '<a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a> ' +
  '<a href="https://www.openmaptiles.org/" target="_blank" rel="noopener">© OpenMapTiles</a> ' +
  'Data from <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>'

/** The base map's place names that LEPTON writes itself inside NCR: its cities and Pateros. */
const NCR_NAME_LAYERS = ['label_city', 'label_city_capital', 'label_town']

/**
 * From this zoom in, LEPTON writes the NCR cities' names (CityMap); further out the 17 names
 * would pile up, so they hide and the base map's own names (Manila, Quezon City) show instead.
 */
export const CITY_NAMES_ZOOM = 8.5

/** The glow around the globe, gone by the time the map shows a region (zoom 7). */
const SKY: SkySpecification = { 'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 1, 5, 1, 7, 0] }

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

/** The colors the base map is drawn in, read from tokens.css: MapLibre draws on a canvas and cannot read CSS variables. */
function mapColors(element: HTMLElement) {
  const style = getComputedStyle(element)
  const color = (token: string) => style.getPropertyValue(`--color-${token}`).trim()
  return { land: color('map-land'), water: color('bg-inset'), road: color('map-boundary') }
}

type MapColors = ReturnType<typeof mapColors>

/** The cities' outlines as one shape, to hide the base map's names inside it. */
function ncrOutline(cities: Cities): MultiPolygon {
  return { type: 'MultiPolygon', coordinates: cities.features.flatMap(({ geometry }) => shapeParts(geometry)) }
}

/**
 * One base map layer in the app's colors. A layer of names LEPTON writes itself becomes two: as
 * it was up to CITY_NAMES_ZOOM, and from there on without the names inside NCR.
 */
function adaptLayer(layer: LayerSpecification, colors: MapColors, ncr: MultiPolygon): LayerSpecification[] {
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
  if (layer.type === 'symbol' && NCR_NAME_LAYERS.includes(layer.id)) {
    const outside = ['!', ['within', ncr]] as FilterSpecification
    const near = {
      ...layer,
      id: `${layer.id}-outside-ncr`,
      minzoom: Math.max(layer.minzoom ?? 0, CITY_NAMES_ZOOM),
      filter: (layer.filter ? ['all', layer.filter, outside] : outside) as FilterSpecification,
    }
    return [{ ...layer, maxzoom: Math.min(layer.maxzoom ?? CITY_NAMES_ZOOM, CITY_NAMES_ZOOM) }, near]
  }
  return [layer]
}

/**
 * The style CityMap makes the map with: the street map adapted to the app, or, without one,
 * the plain background the map had before F13 (bg/inset). Both are globes. `element` is the
 * map's element, for the token colors.
 */
export function mapStyle(base: StyleSpecification | null, element: HTMLElement, cities: Cities): StyleSpecification {
  const colors = mapColors(element)
  const globe: Pick<StyleSpecification, 'projection' | 'sky'> = { projection: { type: 'globe' }, sky: SKY }
  if (!base) {
    return {
      version: 8,
      sources: {},
      layers: [{ id: 'background', type: 'background', paint: { 'background-color': colors.water } }],
      ...globe,
    }
  }
  const ncr = ncrOutline(cities)
  const sources = Object.fromEntries(
    Object.entries(base.sources).map(([id, source]) => [
      id,
      id === BASE_SOURCE ? { ...source, attribution: BASE_ATTRIBUTION } : source,
    ]),
  )
  return { ...base, sources, layers: base.layers.flatMap((layer) => adaptLayer(layer, colors, ncr)), ...globe }
}
