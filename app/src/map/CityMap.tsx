import type {
  ExpressionSpecification,
  StyleSpecification,
  SymbolLayerSpecification,
} from '@maplibre/maplibre-gl-style-spec'
import type { FeatureCollection, Point } from 'geojson'
import type { Map as MapLibreMap, Marker } from 'maplibre-gl'
import { useEffect, useRef, useState, type CSSProperties, type RefObject } from 'react'
import { createPortal } from 'react-dom'
import { Link, useLocation, useNavigate } from 'react-router'
import Badge from '../components/Badge.tsx'
import Icon from '../components/Icon.tsx'
import maplibregl from '../lib/maplibre.ts'
import { barangayLayers } from './barangayLayers.ts'
import { DATA_OPACITY, mapStyle, setBase, type BaseMap } from './basemap.ts'
import { CITIES_ZOOM, addIslands, fadeIn, type Islands } from './borders.ts'
import { CITY_LAYERS as LAYERS, CITY_NAMES_SOURCE as NAMES_SOURCE, CITY_SOURCE as SOURCE } from './cityLayers.ts'
import { featureFader } from './featureFades.ts'
import { LEVEL_NAMES, LEVEL_TONES, isSimulated, levelOf, simulatedLabel } from './forecast.ts'
import { SLOTS, addSlots } from './layerOrder.ts'
import { orbit } from './orbit.ts'
import { TILT, set3D } from './terrain.ts'
import { shortName, type Cities, type CityForecast, type CityProperties, type ForecastWeek } from './mapData.ts'
import { CAMERA_MS, CROSSFADE_MS, DIMMED_OPACITY, HOVER_MS, easeInOut, prefersReducedMotion } from './motion.ts'
import { CITY_PATHS, MAP_PATHS, QC_PSGC, levelSearch, type MapLevel } from './routes.ts'
import { tokenColor } from './tokens.ts'
import { placeTooltip, type MapPointer } from './tooltip.ts'
import { READER_MOVE, cityView, closeCamera, levelCamera, moveToLevel, viewFor } from './view.ts'
import './CityMap.css'

/* The one MapLibre map the three map levels share, with NCR's cities. */

/** How far out the reader may zoom: at 1 the map is the whole world. */
const MIN_ZOOM = 1

/** The credit for the city outlines, shown with the street map's in the map's corner. */
const BOUNDARIES_CREDIT = 'Boundaries: PSA and NAMRIA via OCHA HDX; faeldon/philippines-json-maps'

/** Outline widths in px. */
const LINE = { noData: 1, data: 1.5, hover: 3, open: 2.5 }

/** The outline of the town the search found, in px. */
const FOUND_LINE = { width: 2.5, casing: 6 }

/** The cities' fills keep a smoothed edge. */
const FILL_EDGES: ExpressionSpecification = ['step', ['zoom'], false, CITIES_ZOOM, true]

/** How opaque a city without data is filled: the street map shows through most of the country. */
const NO_DATA_ALPHA = 0.35

/** How long, in ms, a click on empty map waits before it closes the panel: a second click in time is a double click. */
const CLOSE_WAIT_MS = 300

/** The tooltip's width in px, and the most it is tall. */
const TOOLTIP_WIDTH = 256
const TOOLTIP_TALLEST = 150

/** A city's data: feature state "level" (its outbreak level) and "hover" (0 to 1). */
const HAS_DATA: ExpressionSpecification = ['boolean', ['get', 'has_data'], false]
const HOVER: ExpressionSpecification = ['number', ['feature-state', 'hover'], 0]
const REST_WIDTH: ExpressionSpecification = ['case', HAS_DATA, LINE.data, LINE.noData]

/** A city's outline: its resting width, growing to LINE.hover as its hover goes from 0 to 1. */
const LINE_WIDTH: ExpressionSpecification = ['+', REST_WIDTH, ['*', HOVER, ['-', LINE.hover, REST_WIDTH]]]

/** A hex color from tokens.css with an alpha, as MapLibre reads colors: "#e9ebee" at 0.35. */
function withAlpha(hex: string, alpha: number): string {
  const value = hex.trim().replace('#', '')
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(value.slice(i, i + 2), 16))
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

/** The colors the map paints with, read from tokens.css (tokens.ts). */
function tokenColors(element: HTMLElement) {
  const color = (token: string) => tokenColor(element, token)
  return {
    // A city without data lets the street map show through, and turns white under the pointer
    noData: withAlpha(color('bg-raised'), NO_DATA_ALPHA),
    hovered: color('bg-surface'),
    line: color('text-primary'),
    low: color('risk-low'),
    watch: color('risk-watch'),
    high: color('risk-high'),
    // The town the search found
    found: color('accent-primary'),
    foundCasing: color('bg-surface'),
  }
}

type Colors = ReturnType<typeof tokenColors>

/** A city's fill: its outbreak level's color if it has data. */
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

/** Outlines the town `psgc` as the search's find ("" for none). */
function showFound(map: MapLibreMap, psgc: string) {
  map.setFilter(LAYERS.foundCasing, isOpen(psgc))
  map.setFilter(LAYERS.foundLine, isOpen(psgc))
}

/** Fades cities' feature state "hover" between 0 and 1 in HOVER_MS. */
function hoverFader(map: MapLibreMap) {
  return featureFader(map, SOURCE, 'hover', HOVER_MS)
}

/** Moves the hover to the city `psgc` from the city in `hovered`. */
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

/** Keeps the street map's names off the cities' names. */
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

/** The room the cities' names keep (addNameRoom), only at level 1, where the names show. */
function setNameRoom(map: MapLibreMap, level: MapLevel) {
  if (map.getLayer(LAYERS.names)) {
    map.setLayoutProperty(LAYERS.names, 'visibility', level === 1 ? 'visible' : 'none')
  }
}

/** The city under the pointer, and where the pointer is in the map, in px. */
type Pointer = MapPointer & { psgc: string }

/** Where a city's name is written: the element MapLibre keeps over its label point. */
type LabelSpot = { city: CityProperties; element: HTMLElement }

type CityMapProps = {
  cities: Cities
  /** The islands' coastlines, drawn between the country's view and the towns' borders. */
  islands: Islands
  forecast: CityForecast
  /** The street map's style from the loader, or null to draw on a plain background. */
  baseStyle: StyleSpecification | null
  /** The base map chosen in the Layers panel. */
  base: BaseMap
  /** Whether the map is in 3D: the Layers panel's 3D view, or the prophylaxis plan's own (MapLayout). */
  view3d: boolean
  /** The week after the chosen date, or undefined if the backtest has no forecast for it. */
  week: ForecastWeek | undefined
  /** The open level: 1 the Philippines, 2 Quezon City, 3 its prophylaxis plan. */
  level: MapLevel
  /** Called with the map once it has loaded and drawn the cities, and with null when it is removed. */
  onMap: (map: MapLibreMap | null) => void
  /** The legend and zoom buttons' box. */
  controls: RefObject<HTMLElement | null>
  /** The top left corner's box (MapLayout), which the camera keeps the open city clear of too. */
  topBar: RefObject<HTMLElement | null>
  /** The city the search last found (a new object each time it finds one), or null. */
  found: { psgc: string } | null
}

/** The map, the name of the city with data and the city tooltip. */
export default function CityMap({
  cities,
  islands,
  forecast,
  baseStyle,
  base,
  view3d,
  week,
  level,
  onMap,
  controls,
  topBar,
  found,
}: CityMapProps) {
  const navigate = useNavigate()
  const { search } = useLocation()
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const faderRef = useRef<ReturnType<typeof hoverFader> | null>(null)
  const hoveredRef = useRef<string | null>(null)
  const shownLevel = useRef(level) // The level the map is drawn for
  const openRef = useRef({ navigate, search }) // Read by the map's click handler, which is made once
  const [loaded, setLoaded] = useState(false)
  const [spots, setSpots] = useState<LabelSpot[]>([])
  const [pointer, setPointer] = useState<Pointer | null>(null)
  const readerMoved = useRef(false) // The reader has panned, zoomed or turned the map since the camera last fit the level
  const fillOpacity = useRef(DATA_OPACITY[base]) // How opaque the fills are on the base map shown
  const shown3D = useRef<boolean | null>(null) // Whether the map is drawn in 3D; null until first set
  const shownFound = useRef<{ psgc: string } | null>(null) // The search's find the camera last went to

  // The click handler opens a city with the latest navigate and date
  useEffect(() => {
    openRef.current = { navigate, search }
  })

  // Make the map once: the loader's cities never change, and onMap only stores the map.
  useEffect(() => {
    const container = containerRef.current!
    const colors = tokenColors(container)
    const view = viewFor(shownLevel.current, cities, container, controls.current, topBar.current)
    const start = levelCamera(view, container, 0)
    const map = new maplibregl.Map({
      container,
      style: mapStyle(baseStyle, container, cities),
      // A map with no room yet starts on MapLibre's own fit; the first resize then shows the level
      ...(start ? { center: start.center, zoom: start.zoom } : { bounds: view.bounds }),
      minZoom: MIN_ZOOM,
      attributionControl: false,
      // Flat: no turning or tilting.
      dragRotate: false,
      pitchWithRotate: true,
      touchPitch: false,
      renderWorldCopies: false,
      // Names appear at once instead of fading in.
      fadeDuration: 0,
    })
    // The level's padding is the camera's own from the start (view.ts, levelCamera)
    if (start) {
      map.setPadding(view.padding)
    }
    // The sources' credits are in the info pop-up (MapInfo.tsx), not on the map.
    // A move the reader makes comes with their event.
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

    // As soon as the style is ready, not on "load", which also waits for the street map's first tiles.
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
          paint: {
            'fill-color': fillColor(colors),
            'fill-opacity': opacity * fillOpacity.current,
            'fill-antialias': FILL_EDGES,
          },
        },
        SLOTS.fills,
      )
      // The coastlines, then the towns' borders, each from its zoom on (borders.ts)
      addIslands(map, islands, colors.line)
      map.addLayer({
        id: LAYERS.line,
        type: 'line',
        source: SOURCE,
        filter: isNotOpen(open),
        minzoom: CITIES_ZOOM,
        layout: { 'line-join': 'round' },
        paint: { 'line-color': colors.line, 'line-width': LINE_WIDTH, 'line-opacity': fadeIn(CITIES_ZOOM, opacity) },
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
      // The search's town, at every zoom, none at first
      for (const [id, color, width] of [
        [LAYERS.foundCasing, colors.foundCasing, FOUND_LINE.casing],
        [LAYERS.foundLine, colors.found, FOUND_LINE.width],
      ] as const) {
        map.addLayer({
          id,
          type: 'line',
          source: SOURCE,
          filter: isOpen(''),
          layout: { 'line-join': 'round' },
          paint: { 'line-color': color, 'line-width': width },
        })
      }
      // Each city's name sits in an element MapLibre keeps over its label point
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
      setLoaded(true)
      // Only now, so a level that draws its own layers finds the cities' layers in place
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
    // Levels 2 and 3: a click on the map outside the open city closes the panel, as its Close button does.
    // A click on the city (or one of its barangays) does what it did; a drag is no click. With a barangay's
    // pop-up open, the click only closes the pop-up (barangayLayers.ts). The panel closes CLOSE_WAIT_MS
    // after the click, so a double click (or a double tap) zooms instead.
    let closeTimer = 0
    const keepOpen = () => window.clearTimeout(closeTimer)
    map.on('click', (event) => {
      const barangays = barangayLayers(map)
      if (shownLevel.current === 1 || barangays.selection() !== null || barangays.covers(event.point)) {
        return
      }
      if (map.queryRenderedFeatures(event.point, { layers: [LAYERS.openFill] }).length > 0) {
        return
      }
      keepOpen()
      closeTimer = window.setTimeout(
        () => openRef.current.navigate(MAP_PATHS[1] + levelSearch(1, openRef.current.search)),
        CLOSE_WAIT_MS,
      )
    })
    map.on('dblclick', keepOpen)
    map.on('zoomstart', keepOpen)
    // A new map size: show the level's view again, unless the reader has moved away from it
    map.on('resize', () => {
      if (readerMoved.current) {
        return
      }
      const view = viewFor(shownLevel.current, cities, container, controls.current, topBar.current)
      moveToLevel(map, view, shown3D.current ? TILT : 0, { duration: 0 })
    })

    return () => {
      keepOpen()
      fader.stop()
      markers.forEach((marker) => marker.remove())
      map.remove()
      mapRef.current = null
      faderRef.current = null
      hoveredRef.current = null
      // A new map starts flat, on the level's view
      shown3D.current = null
      readerMoved.current = false
      setSpots([])
      setLoaded(false)
      onMap(null)
    }
  }, [cities, islands, baseStyle, onMap, controls, topBar])

  // The base map chosen in the Layers panel.
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

  // The 3D view: the ground rises and the camera tilts.
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
    // On the level's view the camera fits it again, tilted or flat.
    const view = viewFor(shownLevel.current, cities, map.getContainer(), controls.current, topBar.current)
    if (readerMoved.current || !moveToLevel(map, view, pitch, motion)) {
      map.easeTo({ pitch, bearing: view3d ? map.getBearing() : 0, ...motion })
    }
  }, [view3d, loaded, cities, controls, topBar])

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
    const closing = level === 1 // The panel closes
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
    map.setPaintProperty(LAYERS.line, 'line-opacity', fadeIn(CITIES_ZOOM, opacity))
    setNameRoom(map, level)
    // With reduced motion the camera jumps.
    const pitch = view3d ? TILT : 0
    const motion = { duration: CAMERA_MS, easing: easeInOut }
    if (closing) {
      // The camera steps back from the city instead of going to the whole country.
      const country = viewFor(1, cities, map.getContainer(), controls.current, topBar.current)
      map.easeTo({ ...closeCamera(map, country, pitch), ...motion }, READER_MOVE)
    } else {
      moveToLevel(map, viewFor(level, cities, map.getContainer(), controls.current, topBar.current), pitch, motion)
      showFound(map, '') // Opening a city ends the search's mark
    }
    if (level > 1 && faderRef.current) {
      moveHover(faderRef.current, hoveredRef, null)
      map.getCanvas().style.cursor = ''
      setPointer(null)
    }
  }, [level, loaded, cities, controls, topBar, view3d])

  // A city the search found.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loaded || level !== 1 || shownFound.current === found) {
      return
    }
    shownFound.current = found
    showFound(map, found?.psgc ?? '')
    if (!found) {
      return
    }
    const view = cityView(cities, found.psgc, map.getContainer(), controls.current, topBar.current)
    const camera = levelCamera(view, map.getContainer(), view3d ? TILT : 0)
    if (camera) {
      map.easeTo({ ...camera, duration: CAMERA_MS, easing: easeInOut }, READER_MOVE)
    }
  }, [found, level, loaded, cities, controls, topBar, view3d])

  // The prophylaxis plan opens in 3D.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loaded || level !== 3 || !view3d || prefersReducedMotion()) {
      return
    }
    return orbit(map, () => {
      readerMoved.current = true
    })
  }, [level, loaded, view3d])

  const model = week?.forecasts[forecast.map_model]
  const expected = model ? Math.round(model.mu) : null
  return (
    <div
      className="city-map"
      data-level={level}
      data-base={base}
      data-view={view3d ? '3d' : undefined}
    >
      <div ref={containerRef} className="city-map-canvas" />
      {spots.map(({ city, element }) =>
        createPortal(
          CITY_PATHS[city.psgc] ? (
            // A city with data: its name and next week's expected cases, a link for keyboard readers.
            <Link
              to={CITY_PATHS[city.psgc] + search}
              className={`city-map-label city-map-label-open${pointer?.psgc === city.psgc ? ' city-map-label-hovered' : ''}`}
            >
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
          style={placeTooltip(pointer, TOOLTIP_WIDTH, TOOLTIP_TALLEST)}
        />
      )}
    </div>
  )
}

type CityTooltipProps = {
  city: CityProperties
  forecast: CityForecast
  week: ForecastWeek | undefined
  style: CSSProperties
}

/** The tooltip of the city under the pointer. */
function CityTooltip({ city, forecast, week, style }: CityTooltipProps) {
  const model = week?.forecasts[forecast.map_model]
  if (!CITY_PATHS[city.psgc]) {
    return (
      <div className="city-map-tooltip" style={style}>
        <p className="city-map-tooltip-title label-ui">
          <Icon name="no-data" size={18} className="city-map-tooltip-icon" />
          {shortName(city)}
        </p>
        <p className="city-map-tooltip-text body-s">{city.province}</p>
        <p className="city-map-tooltip-text body-s">
          No data yet: LEPTON starts with Quezon City. A forecast here needs this town's weekly case counts.
        </p>
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
      {isSimulated(forecast, week) && (
        <Badge tone="warn" className="city-map-tooltip-badge">
          {simulatedLabel(forecast)}
        </Badge>
      )}
    </div>
  )
}
