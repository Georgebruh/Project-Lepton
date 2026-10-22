import type {
  ExpressionSpecification,
  StyleSpecification,
  SymbolLayerSpecification,
} from '@maplibre/maplibre-gl-style-spec'
import type { FeatureCollection, Point } from 'geojson'
import type { Map as MapLibreMap, Marker } from 'maplibre-gl'
import { useEffect, useRef, useState, type CSSProperties, type Ref, type RefObject } from 'react'
import { createPortal } from 'react-dom'
import { Link, useLocation, useNavigate } from 'react-router'
import Badge from '../components/Badge.tsx'
import Icon from '../components/Icon.tsx'
import { shapeMiddle, shapeParts } from '../exposed/nearest.ts'
import maplibregl from '../lib/maplibre.ts'
import { barangayLayers } from './barangayLayers.ts'
import { CITY_NAMES_ZOOM, DATA_OPACITY, mapStyle, setBase, type BaseMap } from './basemap.ts'
import { CITY_LAYERS as LAYERS, CITY_NAMES_SOURCE as NAMES_SOURCE, CITY_SOURCE as SOURCE } from './cityLayers.ts'
import { featureFader } from './featureFades.ts'
import { LEVEL_NAMES, LEVEL_TONES, SIMULATED_LABEL, levelOf } from './forecast.ts'
import MapList, { type MapListHandle, type MapListItem } from './MapList.tsx'
import { SLOTS, addSlots } from './layerOrder.ts'
import { TILT, set3D } from './terrain.ts'
import { shortName, type Cities, type CityForecast, type CityProperties, type ForecastWeek } from './mapData.ts'
import { CAMERA_MS, CROSSFADE_MS, DIMMED_OPACITY, HOVER_MS, SHEET_BELOW, easeInOut, prefersReducedMotion } from './motion.ts'
import { CITY_PATHS, QC_PSGC, type MapLevel } from './routes.ts'
import { tokenColor } from './tokens.ts'
import { placeTooltip, type MapPointer } from './tooltip.ts'
import { levelCamera, moveToLevel, viewFor } from './view.ts'
import './CityMap.css'

/*
 * F4: the one MapLibre map the three map levels share, with NCR's cities (Figma frames 1, 1a,
 * 1b and 2, and the notes "Map drill-down · design notes", node 58:447).
 *
 * The cities are one GeoJSON source keyed on PSGC (promoteId), drawn by two pairs of fill and
 * line layers: "cities" for every city but the open one, and "city-open" for the open one
 * (Quezon City, at levels 2 and 3). Opening a city fades the first pair to 45% (a plain paint
 * transition) while the camera fits the open city beside the panel, all in 700 ms. The ids are
 * in cityLayers.ts, since F5's barangay layers go between them.
 *
 * MapLibre redraws a feature-state change at once: its paint transitions skip any value that
 * differs from city to city. So the hover's 150 ms fade is played frame by frame
 * (featureFades.ts), and the fade to 45% uses a layer-wide value, not a per-city one.
 *
 * F13: the cities sit on the street map (basemap.ts), and the reader may pan anywhere and zoom
 * out to the whole world. The fills go in over the street map's roads and under its names, the
 * outlines on top (layerOrder.ts). Zoomed out past CITY_NAMES_ZOOM the cities' names hide, since they
 * would pile up. The credits for the map's sources sit behind an "i" in its bottom left corner.
 * On the satellite and terrain base maps (the Layers panel) the fills let the ground show through
 * (DATA_OPACITY). The cities' names have a halo, and keep the street map's names off them
 * (addNameRoom). In the 3D view (terrain.ts) the camera tilts,
 * and a level's view keeps the tilt and faces north (view.ts, moveToLevel).
 */

/** How far out the reader may zoom: at 1 the map is the whole world. */
const MIN_ZOOM = 1

/** The credit for the city outlines, shown with the street map's in the map's corner. */
const BOUNDARIES_CREDIT = 'Boundaries: PSA and NAMRIA via OCHA HDX; faeldon/philippines-json-maps'

/** Outline widths in px, from Figma: a city without data 1, with data 1.5, under the pointer 3, open 2.5. */
const LINE = { noData: 1, data: 1.5, hover: 3, open: 2.5 }

/** The tooltip's width in px (Figma), and the most it is tall. */
const TOOLTIP_WIDTH = 256
const TOOLTIP_TALLEST = 150

/** A city's data: feature state "level" (its outbreak level) and "hover" (0 to 1). */
const HAS_DATA: ExpressionSpecification = ['boolean', ['get', 'has_data'], false]
const HOVER: ExpressionSpecification = ['number', ['feature-state', 'hover'], 0]
const REST_WIDTH: ExpressionSpecification = ['case', HAS_DATA, LINE.data, LINE.noData]

/** A city's outline: its resting width, growing to LINE.hover as its hover goes from 0 to 1. */
const LINE_WIDTH: ExpressionSpecification = ['+', REST_WIDTH, ['*', HOVER, ['-', LINE.hover, REST_WIDTH]]]

/** The colors the map paints with, read from tokens.css (tokens.ts). */
function tokenColors(element: HTMLElement) {
  const color = (token: string) => tokenColor(element, token)
  return {
    noData: color('bg-raised'),
    hovered: color('bg-surface'),
    line: color('text-primary'),
    low: color('risk-low'),
    watch: color('risk-watch'),
    high: color('risk-high'),
  }
}

type Colors = ReturnType<typeof tokenColors>

/** A city's fill: its outbreak level's color if it has data; if not, grey, turning white under the pointer. */
function fillColor(colors: Colors): ExpressionSpecification {
  const level: ExpressionSpecification = ['string', ['feature-state', 'level'], 'none']
  return [
    'case',
    HAS_DATA,
    ['match', level, 'low', colors.low, 'watch', colors.watch, 'high', colors.high, colors.noData],
    ['interpolate', ['linear'], HOVER, 0, colors.noData, 1, colors.hovered],
  ]
}

/** The filters that put the open city ("" for none) in the "city-open" layers and the rest in "cities". */
function isOpen(psgc: string): ExpressionSpecification {
  return ['==', ['get', 'psgc'], psgc]
}

function isNotOpen(psgc: string): ExpressionSpecification {
  return ['!=', ['get', 'psgc'], psgc]
}

/**
 * Fades cities' feature state "hover" between 0 and 1 in HOVER_MS, a step each frame.
 * fade(psgc, 1) starts a city's hover, fade(psgc, 0) ends it.
 */
function hoverFader(map: MapLibreMap) {
  return featureFader(map, SOURCE, 'hover', HOVER_MS)
}

/**
 * Moves the hover to the city `psgc` (null: to none) from the city in `hovered`: the one's
 * outline thins as the other's thickens. The pointer and, F11, the list of cities both move it.
 */
function moveHover(fader: ReturnType<typeof hoverFader>, hovered: { current: string | null }, psgc: string | null) {
  if (psgc === hovered.current) {
    return
  }
  if (hovered.current) {
    fader.fade(hovered.current, 0)
  }
  if (psgc) {
    fader.fade(psgc, 1)
  }
  hovered.current = psgc
}

/** A stand-in for a city's cases line in addNameRoom, as wide as a three-digit count. */
const CASES_ROOM = '000 cases next week'

/**
 * F13: keeps the street map's names off the cities' names. LEPTON's names are HTML over the map
 * (links, for the keyboard), which MapLibre's own labels cannot see, so a town just outside NCR
 * printed over Quezon City's cases (San Mateo). This adds an invisible copy of each name, and of
 * the cases line for a city with data, at its label point and on top of every layer: MapLibre
 * places the top layer's labels first, always places these (allow-overlap), and drops any street
 * map name that would run into them. It shows where the HTML names do: at level 1 (setNameRoom),
 * from CITY_NAMES_ZOOM in. It needs the street map's fonts; without the street map (it did not
 * load) there are no names to keep off, and it is not added.
 */
function addNameRoom(map: MapLibreMap, cities: Cities, level: MapLevel) {
  const style = map.getStyle()
  const named = style.layers.find(
    (layer): layer is SymbolLayerSpecification => layer.type === 'symbol' && layer.layout?.['text-font'] !== undefined,
  )
  if (!style.glyphs || !named) {
    return
  }
  const points: FeatureCollection<Point> = {
    type: 'FeatureCollection',
    features: cities.features.flatMap(({ properties: city }) =>
      city.label_lon === null || city.label_lat === null
        ? []
        : [
            {
              type: 'Feature' as const,
              geometry: { type: 'Point' as const, coordinates: [city.label_lon, city.label_lat] },
              properties: { text: CITY_PATHS[city.psgc] ? `${shortName(city)}\n${CASES_ROOM}` : shortName(city) },
            },
          ],
    ),
  }
  map.addSource(NAMES_SOURCE, { type: 'geojson', data: points })
  map.addLayer({
    id: LAYERS.names,
    type: 'symbol',
    source: NAMES_SOURCE,
    minzoom: CITY_NAMES_ZOOM,
    layout: {
      visibility: level === 1 ? 'visible' : 'none',
      'text-field': ['get', 'text'],
      'text-font': named.layout!['text-font'],
      // Label/UI's 14 px on 20 px lines, as the HTML names (CityMap.css); one line each, never wrapped
      'text-size': 14,
      'text-line-height': 20 / 14,
      'text-max-width': 100,
      'text-padding': 4,
      'text-allow-overlap': true,
    },
    paint: { 'text-opacity': 0 },
  })
}

/** F13: the room the cities' names keep (addNameRoom), only at level 1, where the names show. */
function setNameRoom(map: MapLibreMap, level: MapLevel) {
  if (map.getLayer(LAYERS.names)) {
    map.setLayoutProperty(LAYERS.names, 'visibility', level === 1 ? 'visible' : 'none')
  }
}

/** F11: the list's rows, the cities with a forecast first, then the others by name. */
function cityItems(cities: Cities, forecast: CityForecast, week: ForecastWeek | undefined): MapListItem[] {
  const model = week?.forecasts[forecast.map_model]
  const simulated = forecast.simulated ? ` (${SIMULATED_LABEL})` : ''
  const items: MapListItem[] = cities.features.map(({ properties: city }) => {
    if (!CITY_PATHS[city.psgc]) {
      const detail = <span className="body-s">No data yet</span>
      return { id: city.psgc, name: shortName(city), detail, words: 'no data yet' }
    }
    if (!model) {
      return { id: city.psgc, name: shortName(city), words: 'no forecast for the week after this date', opens: true }
    }
    const level = levelOf(model.p_breach, forecast.levels)
    return {
      id: city.psgc,
      name: shortName(city),
      detail: <Badge tone={LEVEL_TONES[level]}>{LEVEL_NAMES[level]}</Badge>,
      words: `${LEVEL_NAMES[level]} chance of an outbreak, ${Math.round(model.mu)} cases expected next week${simulated}`,
      opens: true,
    }
  })
  return items.sort((a, b) => Number(Boolean(b.opens)) - Number(Boolean(a.opens)) || a.name.localeCompare(b.name))
}

/** The city under the pointer, and where the pointer is in the map, in px; F11: or the city the list shows. */
type Pointer = MapPointer & { psgc: string; fromList?: boolean }

/** Where a city's name is written: the element MapLibre keeps over its label point. */
type LabelSpot = { city: CityProperties; element: HTMLElement }

type CityMapProps = {
  cities: Cities
  forecast: CityForecast
  /** F13: the street map's style from the loader, or null to draw on a plain background. */
  baseStyle: StyleSpecification | null
  /** F13: the base map chosen in the Layers panel. */
  base: BaseMap
  /** F13: whether the Layers panel's 3D view is on. */
  view3d: boolean
  /** The week after the chosen date, or undefined if the backtest has no forecast for it. */
  week: ForecastWeek | undefined
  /** The open level: 1 Metro Manila, 2 Quezon City, 3 its prophylaxis plan. */
  level: MapLevel
  /** Called with the map once it has loaded and drawn the cities, and with null when it is removed. */
  onMap: (map: MapLibreMap | null) => void
  /** F11: the legend and zoom buttons' box (MapLayout), which on a phone the camera keeps the open city clear of. */
  controls: RefObject<HTMLElement | null>
  /** F11: the list of cities, which MapLayout moves the keyboard to when the reader comes back to level 1. */
  listRef: Ref<MapListHandle>
  /** F11: called with the box under the hint where a level puts its own list (F5's barangays), and null when it goes. */
  onListSlot: (slot: HTMLElement | null) => void
}

/**
 * F4: the map, its city names, the hint and the city tooltip. At level 1, hovering a city
 * thickens its outline and shows its tooltip; clicking a city with data opens its forecast.
 * When the level changes, the camera and the cities move as the Figma notes say.
 *
 * F11: under the hint, the list of cities reaches each of them without a mouse (MapList): the
 * city reached thickens and shows its tooltip, as under the pointer, and Enter opens a city with
 * a forecast. The prophylaxis plan puts its list of barangays in the same corner (onListSlot).
 */
export default function CityMap({
  cities,
  forecast,
  baseStyle,
  base,
  view3d,
  week,
  level,
  onMap,
  controls,
  listRef,
  onListSlot,
}: CityMapProps) {
  const navigate = useNavigate()
  const { search } = useLocation()
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const faderRef = useRef<ReturnType<typeof hoverFader> | null>(null)
  const hoveredRef = useRef<string | null>(null)
  const shownLevel = useRef(level) // the level the map is drawn for
  const openRef = useRef({ navigate, search }) // read by the map's click handler, which is made once
  const [loaded, setLoaded] = useState(false)
  const [spots, setSpots] = useState<LabelSpot[]>([])
  const [pointer, setPointer] = useState<Pointer | null>(null)
  const [farOut, setFarOut] = useState(false) // F13: zoomed out past CITY_NAMES_ZOOM
  const readerMoved = useRef(false) // F13: the reader has panned, zoomed or turned the map since the camera last fit the level
  const fillOpacity = useRef(DATA_OPACITY[base]) // F13: how opaque the fills are on the base map shown
  const shown3D = useRef<boolean | null>(null) // F13: whether the map is drawn in 3D; null until first set

  // The click handler opens a city with the latest navigate and date
  useEffect(() => {
    openRef.current = { navigate, search }
  })

  // Make the map once: the loader's cities never change, and onMap only stores the map. React
  // runs this twice in development (StrictMode): the cleanup removes the first map.
  useEffect(() => {
    const container = containerRef.current!
    const colors = tokenColors(container)
    const view = viewFor(shownLevel.current, cities, container, controls.current)
    const start = levelCamera(view, container, 0)
    const map = new maplibregl.Map({
      container,
      style: mapStyle(baseStyle, container, cities),
      // A map with no room yet starts on MapLibre's own fit; the first resize then shows the level
      ...(start ? { center: start.center, zoom: start.zoom } : { bounds: view.bounds }),
      minZoom: MIN_ZOOM,
      attributionControl: false,
      // Flat: no turning or tilting. F13: the 3D view turns both on (terrain.ts), and with
      // pitchWithRotate a mouse drag that turns the map tilts it too
      dragRotate: false,
      pitchWithRotate: true,
      touchPitch: false,
      renderWorldCopies: false,
      // F13: names appear at once instead of fading in. A fade redraws the map for 300 ms after
      // every change of which names fit, and on the street map's thousands of names that kept
      // the map drawing through most of a pan
      fadeDuration: 0,
    })
    // F13: the level's padding is the camera's own from the start (view.ts, levelCamera)
    if (start) {
      map.setPadding(view.padding)
    }
    // F13: the sources' credits, bottom left, folded behind an "i" button: written out, they are
    // wide enough to run into the legend on a laptop with the panel open
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-left')
    // MapLibre opens them when they first arrive and closes them on the first drag; here they start closed
    const closeCredits = () => {
      const credits = container.querySelector('.maplibregl-ctrl-attrib')
      if (credits?.classList.contains('maplibregl-compact')) {
        credits.classList.remove('maplibregl-compact-show')
        map.off('sourcedata', closeCredits)
      }
    }
    map.on('sourcedata', closeCredits)
    map.on('zoom', () => setFarOut(map.getZoom() < CITY_NAMES_ZOOM))
    // A move the reader makes comes with their event (a drag, a pinch, a key) or, F13, is the zoom
    // buttons' (READER_MOVE); a wheel zoom says so through its own event. A move to the level's
    // view (a level, the pin) carries LEVEL_FIT. MapLibre's own moves, such as a resize or the 3D
    // view's tilt, change nothing (view.ts)
    map.on('movestart', (event) => {
      if (event.originalEvent || 'readerMove' in event) {
        readerMoved.current = true
      } else if ('levelFit' in event) {
        readerMoved.current = false
      }
    })
    map.on('wheel', () => {
      readerMoved.current = true
    })
    map.touchZoomRotate.disableRotation()
    map.keyboard.disableRotation()
    const fader = hoverFader(map)
    const markers: Marker[] = []
    mapRef.current = map
    faderRef.current = fader

    // F13: as soon as the style is ready, not on "load", which also waits for the street map's
    // first tiles: a slow tile server must not hold back LEPTON's data
    map.once('style.load', () => {
      const open = shownLevel.current > 1 ? QC_PSGC : ''
      const opacity = shownLevel.current > 1 ? DIMMED_OPACITY : 1
      addSlots(map)
      map.addSource(SOURCE, { type: 'geojson', data: cities, promoteId: 'psgc', attribution: BOUNDARIES_CREDIT })
      map.addLayer(
        {
          id: LAYERS.fill,
          type: 'fill',
          source: SOURCE,
          filter: isNotOpen(open),
          paint: { 'fill-color': fillColor(colors), 'fill-opacity': opacity * fillOpacity.current },
        },
        SLOTS.fills,
      )
      map.addLayer({
        id: LAYERS.line,
        type: 'line',
        source: SOURCE,
        filter: isNotOpen(open),
        layout: { 'line-join': 'round' },
        paint: { 'line-color': colors.line, 'line-width': LINE_WIDTH, 'line-opacity': opacity },
      })
      map.addLayer(
        {
          id: LAYERS.openFill,
          type: 'fill',
          source: SOURCE,
          filter: isOpen(open),
          paint: { 'fill-color': fillColor(colors), 'fill-opacity': fillOpacity.current },
        },
        SLOTS.fills,
      )
      map.addLayer({
        id: LAYERS.openLine,
        type: 'line',
        source: SOURCE,
        filter: isOpen(open),
        layout: { 'line-join': 'round' },
        paint: { 'line-color': colors.line, 'line-width': LINE.open },
      })
      // Each city's name sits in an element MapLibre keeps over its label point (F2's label_lon, label_lat)
      const labelSpots: LabelSpot[] = []
      for (const { properties: city } of cities.features) {
        if (city.label_lon === null || city.label_lat === null) {
          continue
        }
        const element = document.createElement('div')
        element.className = 'city-map-spot'
        markers.push(new maplibregl.Marker({ element }).setLngLat([city.label_lon, city.label_lat]).addTo(map))
        labelSpots.push({ city, element })
      }
      addNameRoom(map, cities, shownLevel.current)
      setSpots(labelSpots)
      setFarOut(map.getZoom() < CITY_NAMES_ZOOM) // a short map can start zoomed out that far
      setLoaded(true)
      // Only now, so a level that draws its own layers (F5) finds the cities' layers in place
      onMap(map)
    })

    // Level 1: hovering a city thickens its outline and shows its tooltip
    map.on('mousemove', LAYERS.fill, (event) => {
      const feature = event.features?.[0]
      if (shownLevel.current !== 1 || !feature) {
        return
      }
      const psgc = String(feature.properties.psgc)
      moveHover(fader, hoveredRef, psgc)
      map.getCanvas().style.cursor = CITY_PATHS[psgc] ? 'pointer' : ''
      setPointer({ psgc, x: event.point.x, y: event.point.y, width: container.clientWidth, height: container.clientHeight })
    })
    map.on('mouseleave', LAYERS.fill, () => {
      moveHover(fader, hoveredRef, null)
      map.getCanvas().style.cursor = ''
      setPointer(null)
    })
    // Level 1: clicking a city with data opens its forecast, keeping the chosen date
    map.on('click', LAYERS.fill, (event) => {
      const path = CITY_PATHS[String(event.features?.[0]?.properties.psgc)]
      if (shownLevel.current === 1 && path) {
        openRef.current.navigate(path + openRef.current.search)
      }
    })
    // A new map size: show the level's view again, unless the reader has moved away from it
    // (F13: a phone's address bar that shows or hides must not undo their panning)
    map.on('resize', () => {
      if (readerMoved.current) {
        return
      }
      const view = viewFor(shownLevel.current, cities, container, controls.current)
      moveToLevel(map, view, shown3D.current ? TILT : 0, { duration: 0 })
    })

    return () => {
      fader.stop()
      markers.forEach((marker) => marker.remove())
      map.remove()
      mapRef.current = null
      faderRef.current = null
      hoveredRef.current = null
      // F13: a new map starts flat, on the level's view
      shown3D.current = null
      readerMoved.current = false
      setSpots([])
      setLoaded(false)
      onMap(null)
    }
  }, [cities, baseStyle, onMap, controls])

  // F13: the base map chosen in the Layers panel (shaded in 3D), and the fills' opacity over it (a
  // 150 ms crossfade). barangayLayers sets the open city's fill, which at level 3 fades out under the barangays.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loaded) {
      return
    }
    setBase(map, base, view3d)
    fillOpacity.current = DATA_OPACITY[base]
    const fade = { duration: CROSSFADE_MS, delay: 0 }
    map.setPaintProperty(LAYERS.fill, 'fill-opacity-transition', fade)
    map.setPaintProperty(LAYERS.fill, 'fill-opacity', (shownLevel.current > 1 ? DIMMED_OPACITY : 1) * fillOpacity.current)
    barangayLayers(map).setFillOpacity(fillOpacity.current)
  }, [base, view3d, loaded])

  // F13: the 3D view: the ground rises and the camera tilts, on the level's view if the reader has
  // not moved from it, or else where it is, so a neighbourhood they zoomed into stands up (700 ms;
  // with reduced motion MapLibre jumps). Leaving it, the map turns flat and faces north. A page
  // that opens in 3D starts tilted.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loaded || shown3D.current === view3d) {
      return
    }
    const first = shown3D.current === null
    shown3D.current = view3d
    set3D(map, view3d)
    if (first && !view3d) {
      return
    }
    const pitch = view3d ? TILT : 0
    const motion = { duration: first ? 0 : CAMERA_MS, easing: easeInOut }
    // On the level's view the camera fits it again, tilted or flat; moved away from it (or with no
    // room to fit it), it tilts where it is
    const view = viewFor(shownLevel.current, cities, map.getContainer(), controls.current)
    if (readerMoved.current || !moveToLevel(map, view, pitch, motion)) {
      map.easeTo({ pitch, bearing: view3d ? map.getBearing() : 0, ...motion })
    }
  }, [view3d, loaded, cities, controls])

  // Color the city with data by its outbreak level for the chosen week
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loaded) {
      return
    }
    const p = week?.forecasts[forecast.map_model]?.p_breach
    map.setFeatureState({ source: SOURCE, id: QC_PSGC }, { level: p === undefined ? 'none' : levelOf(p, forecast.levels) })
  }, [loaded, week, forecast])

  // Open or leave a city: move the camera, fade the other cities, end any hover
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loaded || shownLevel.current === level) {
      return
    }
    shownLevel.current = level
    const open = level > 1 ? QC_PSGC : ''
    map.setFilter(LAYERS.fill, isNotOpen(open))
    map.setFilter(LAYERS.line, isNotOpen(open))
    map.setFilter(LAYERS.openFill, isOpen(open))
    map.setFilter(LAYERS.openLine, isOpen(open))
    const fade = { duration: prefersReducedMotion() ? CROSSFADE_MS : CAMERA_MS, delay: 0 }
    const opacity = level > 1 ? DIMMED_OPACITY : 1
    map.setPaintProperty(LAYERS.fill, 'fill-opacity-transition', fade)
    map.setPaintProperty(LAYERS.fill, 'fill-opacity', opacity * fillOpacity.current)
    map.setPaintProperty(LAYERS.line, 'line-opacity-transition', fade)
    map.setPaintProperty(LAYERS.line, 'line-opacity', opacity)
    setNameRoom(map, level)
    // With reduced motion the camera jumps. F13: the view keeps the 3D view's tilt (its target,
    // should the tilt still be under way)
    moveToLevel(map, viewFor(level, cities, map.getContainer(), controls.current), view3d ? TILT : 0, {
      duration: CAMERA_MS,
      easing: easeInOut,
    })
    if (level > 1 && faderRef.current) {
      moveHover(faderRef.current, hoveredRef, null)
      map.getCanvas().style.cursor = ''
      setPointer(null)
    }
  }, [level, loaded, cities, controls, view3d])

  /**
   * F11: shows a city from the list as the pointer would: its outline thickens and its tooltip
   * shows at its label point (for Pateros, which has none, a point inside it); null hides it.
   */
  function showCity(psgc: string | null) {
    const map = mapRef.current
    const container = containerRef.current
    if (!map || !container || !faderRef.current || shownLevel.current !== 1) {
      return
    }
    moveHover(faderRef.current, hoveredRef, psgc)
    const city = cities.features.find((feature) => feature.properties.psgc === psgc)
    if (!city) {
      setPointer(null)
      return
    }
    const { label_lon: lon, label_lat: lat } = city.properties
    const spot = lon !== null && lat !== null ? [lon, lat] : shapeMiddle(shapeParts(city.geometry))
    const { x, y } = map.project([spot[0], spot[1]])
    const { clientWidth: width, clientHeight: height } = container
    // On a phone the open list covers the map, and a tooltip would cover the list: the outline shows the city
    setPointer(width < SHEET_BELOW ? null : { psgc: city.properties.psgc, x, y, width, height, fromList: true })
  }

  const model = week?.forecasts[forecast.map_model]
  const expected = model ? Math.round(model.mu) : null
  return (
    <div
      className="city-map"
      data-level={level}
      data-far={farOut || undefined}
      data-base={base}
      data-view={view3d ? '3d' : undefined}
    >
      <div ref={containerRef} className="city-map-canvas" />
      <div className="city-map-corner">
        <p className="city-map-hint body-s">
          <Icon name="info" size={16} />
          {/* F11: a touch screen cannot hover; a tap shows a city's tooltip, or opens a city with data */}
          <span className="city-map-hint-pointer">Hover a city to check its data · click a city to open its forecast</span>
          <span className="city-map-hint-touch">Tap a city to check its data or open its forecast</span>
        </p>
        <div className="city-map-cities">
          <MapList
            ref={listRef}
            title="Cities"
            items={cityItems(cities, forecast, week)}
            note={forecast.simulated && <Badge tone="warn">{SIMULATED_LABEL}</Badge>}
            instructions="The arrow keys or a city's first letters move through the list; Enter opens a city's forecast."
            onShow={showCity}
            onOpen={(psgc) => navigate(CITY_PATHS[psgc] + search)}
          />
        </div>
        {/* F11: the prophylaxis plan's list of barangays goes here (MapProphylaxis) */}
        <div ref={onListSlot} className="city-map-list-slot" />
      </div>
      {spots.map(({ city, element }) =>
        createPortal(
          CITY_PATHS[city.psgc] ? (
            // A city with data: its name and next week's expected cases, a link for keyboard readers
            <Link to={CITY_PATHS[city.psgc] + search} className="city-map-label city-map-label-open">
              <span className="label-ui">{shortName(city)}</span>
              {expected !== null && <span className="city-map-label-cases body-s">{expected} cases next week</span>}
            </Link>
          ) : (
            <span
              className={`city-map-label label-ui-s${pointer?.psgc === city.psgc ? ' city-map-label-hovered' : ''}`}
            >
              {shortName(city)}
            </span>
          ),
          element,
          city.psgc,
        ),
      )}
      {pointer && level === 1 && (
        <CityTooltip
          key={pointer.psgc}
          city={cities.features.find((feature) => feature.properties.psgc === pointer.psgc)!.properties}
          forecast={forecast}
          week={week}
          fromList={pointer.fromList ?? false}
          style={placeTooltip(pointer, TOOLTIP_WIDTH, TOOLTIP_TALLEST, pointer.width)}
        />
      )}
    </div>
  )
}

type CityTooltipProps = {
  city: CityProperties
  forecast: CityForecast
  week: ForecastWeek | undefined
  /** F11: whether the list of cities shows it, where Enter opens the forecast, not a click. */
  fromList: boolean
  style: CSSProperties
}

/**
 * F4: the tooltip of the city under the pointer. Figma 1a: a city without data says so. Figma
 * 1b: a city with data shows its outbreak level and next week's expected cases. While the
 * forecasts are simulated it carries the amber badge (app check U2), which Figma's 1b lacks.
 */
function CityTooltip({ city, forecast, week, fromList, style }: CityTooltipProps) {
  const model = week?.forecasts[forecast.map_model]
  if (!CITY_PATHS[city.psgc]) {
    return (
      <div className="city-map-tooltip" style={style}>
        <p className="city-map-tooltip-title label-ui">
          <Icon name="no-data" size={18} className="city-map-tooltip-icon" />
          {shortName(city)}
        </p>
        <p className="city-map-tooltip-text body-s">No data yet. A forecast needs this city's weekly case counts.</p>
      </div>
    )
  }
  const level = model ? levelOf(model.p_breach, forecast.levels) : null
  return (
    <div className="city-map-tooltip" style={style}>
      <div className="city-map-tooltip-title label-ui">
        {shortName(city)}
        {level && (
          <Badge tone={LEVEL_TONES[level]} className="city-map-tooltip-level">
            {LEVEL_NAMES[level]}
          </Badge>
        )}
      </div>
      {model ? (
        <p className="city-map-tooltip-value">
          <span className="data-l">{Math.round(model.mu)}</span>
          <span className="city-map-tooltip-text body-s">cases expected next week</span>
        </p>
      ) : (
        <p className="city-map-tooltip-text body-s">No forecast for the week after this date.</p>
      )}
      {forecast.simulated && (
        <Badge tone="warn" className="city-map-tooltip-badge">
          {SIMULATED_LABEL}
        </Badge>
      )}
      <p className="city-map-tooltip-hint body-s">{fromList ? 'Press Enter' : 'Click'} to open the forecast</p>
    </div>
  )
}
