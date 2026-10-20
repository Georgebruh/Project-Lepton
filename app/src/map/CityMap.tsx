import type { ExpressionSpecification } from '@maplibre/maplibre-gl-style-spec'
import type { LngLatBoundsLike, Map as MapLibreMap, Marker, PaddingOptions } from 'maplibre-gl'
import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { createPortal } from 'react-dom'
import { Link, useLocation, useNavigate } from 'react-router'
import Badge from '../components/Badge.tsx'
import Icon from '../components/Icon.tsx'
import maplibregl from '../lib/maplibre.ts'
import { LEVEL_NAMES, LEVEL_TONES, SIMULATED_LABEL, levelOf } from './forecast.ts'
import { shortName, type Cities, type CityForecast, type CityProperties, type ForecastWeek } from './mapData.ts'
import {
  CAMERA_MS,
  CROSSFADE_MS,
  DIMMED_OPACITY,
  HOVER_MS,
  PANEL_WIDTH,
  easeInOut,
  prefersReducedMotion,
} from './motion.ts'
import { CITY_PATHS, QC_PSGC, type MapLevel } from './routes.ts'
import './CityMap.css'

/*
 * F4: the one MapLibre map the three map levels share, with NCR's cities (Figma frames 1, 1a,
 * 1b and 2, and the notes "Map drill-down · design notes", node 58:447).
 *
 * The cities are one GeoJSON source keyed on PSGC (promoteId), drawn by two pairs of fill and
 * line layers: "cities" for every city but the open one, and "city-open" for the open one
 * (Quezon City, at levels 2 and 3). Opening a city fades the first pair to 45% (a plain paint
 * transition) while the camera fits the open city beside the panel, all in 700 ms.
 *
 * MapLibre redraws a feature-state change at once: its paint transitions skip any value that
 * differs from city to city. So the hover's 150 ms fade is played frame by frame here
 * (hoverFader), and the fade to 45% uses a layer-wide value, not a per-city one.
 */

const SOURCE = 'cities'
const LAYERS = { fill: 'cities-fill', line: 'cities-line', openFill: 'city-open-fill', openLine: 'city-open-line' }

/** Outline widths in px, from Figma: a city without data 1, with data 1.5, under the pointer 3, open 2.5. */
const LINE = { noData: 1, data: 1.5, hover: 3, open: 2.5 }

/** Space kept around what the camera fits, in px (Figma: 28 around Metro Manila, 32 around Quezon City). */
const FIT_PADDING = { metro: 28, city: 32 }

/**
 * How far past Metro Manila the reader may pan, in degrees (about 110 km). MapLibre keeps the
 * whole view inside this box, so it must stay wider than a wide screen's view of all of Metro
 * Manila (about 0.9 degrees across at 1440 px), or the first view could not fit the city.
 */
const PAN_MARGIN_DEG = 1

/** The tooltip's width in px (Figma), its distance from the pointer and the edges, and the most it is tall. */
const TOOLTIP_WIDTH = 256
const TOOLTIP_GAP = 16
const TOOLTIP_TALLEST = 150

/** A city's data: feature state "level" (its outbreak level) and "hover" (0 to 1). */
const HAS_DATA: ExpressionSpecification = ['boolean', ['get', 'has_data'], false]
const HOVER: ExpressionSpecification = ['number', ['feature-state', 'hover'], 0]
const REST_WIDTH: ExpressionSpecification = ['case', HAS_DATA, LINE.data, LINE.noData]

/** A city's outline: its resting width, growing to LINE.hover as its hover goes from 0 to 1. */
const LINE_WIDTH: ExpressionSpecification = ['+', REST_WIDTH, ['*', HOVER, ['-', LINE.hover, REST_WIDTH]]]

/** The colors the map paints with, read from tokens.css: MapLibre draws on a canvas and cannot read CSS variables. */
function tokenColors(element: HTMLElement) {
  const style = getComputedStyle(element)
  const color = (token: string) => style.getPropertyValue(`--color-${token}`).trim()
  return {
    background: color('bg-inset'),
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

/** The box around some cities' outlines: [[west, south], [east, north]]. */
function boundsOf(features: Cities['features']): [[number, number], [number, number]] {
  let [west, south, east, north] = [Infinity, Infinity, -Infinity, -Infinity]
  for (const { geometry } of features) {
    const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates
    for (const [lon, lat] of polygons.flat(2)) {
      west = Math.min(west, lon)
      east = Math.max(east, lon)
      south = Math.min(south, lat)
      north = Math.max(north, lat)
    }
  }
  return [
    [west, south],
    [east, north],
  ]
}

/**
 * What the camera shows at a level: all of Metro Manila at level 1; the open city at levels 2
 * and 3, kept clear of the panel by right padding the panel's width (unless the screen is too
 * narrow to leave room beside it).
 */
function viewFor(level: MapLevel, cities: Cities, width: number): { bounds: LngLatBoundsLike; padding: PaddingOptions } {
  if (level === 1) {
    const pad = FIT_PADDING.metro
    return { bounds: boundsOf(cities.features), padding: { top: pad, bottom: pad, left: pad, right: pad } }
  }
  const pad = FIT_PADDING.city
  const open = cities.features.filter((feature) => feature.properties.psgc === QC_PSGC)
  const right = width > PANEL_WIDTH * 1.5 ? PANEL_WIDTH + pad : pad
  return { bounds: boundsOf(open), padding: { top: pad, bottom: pad, left: pad, right } }
}

/**
 * Fades cities' feature state "hover" between 0 and 1 in HOVER_MS, a step each frame.
 * fade(psgc, 1) starts a city's hover, fade(psgc, 0) ends it.
 */
function hoverFader(map: MapLibreMap) {
  const now = new Map<string, number>() // each city's hover at this frame
  const goal = new Map<string, number>() // where each fading city is going
  let frame = 0
  let last = 0
  function step(time: number) {
    const move = last ? (time - last) / HOVER_MS : 0
    last = time
    for (const [psgc, target] of goal) {
      const from = now.get(psgc) ?? 0
      const next = target > from ? Math.min(target, from + move) : Math.max(target, from - move)
      now.set(psgc, next)
      map.setFeatureState({ source: SOURCE, id: psgc }, { hover: next })
      if (next === target) {
        goal.delete(psgc)
      }
    }
    frame = goal.size ? requestAnimationFrame(step) : 0
    if (!frame) {
      last = 0
    }
  }
  return {
    fade(psgc: string, target: number) {
      goal.set(psgc, target)
      if (!frame) {
        frame = requestAnimationFrame(step)
      }
    },
    stop() {
      cancelAnimationFrame(frame)
    },
  }
}

/** The city under the pointer, and where the pointer is in the map, in px. */
type Pointer = { psgc: string; x: number; y: number; width: number; height: number }

/** Where a city's name is written: the element MapLibre keeps over its label point. */
type LabelSpot = { city: CityProperties; element: HTMLElement }

type CityMapProps = {
  cities: Cities
  forecast: CityForecast
  /** The week after the chosen date, or undefined if the backtest has no forecast for it. */
  week: ForecastWeek | undefined
  /** The open level: 1 Metro Manila, 2 Quezon City, 3 its prophylaxis plan. */
  level: MapLevel
  /** Called with the map once it is made, and with null when it is removed. */
  onMap: (map: MapLibreMap | null) => void
}

/**
 * F4: the map, its city names, the hint and the city tooltip. At level 1, hovering a city
 * thickens its outline and shows its tooltip; clicking a city with data opens its forecast.
 * When the level changes, the camera and the cities move as the Figma notes say.
 */
export default function CityMap({ cities, forecast, week, level, onMap }: CityMapProps) {
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

  // The click handler opens a city with the latest navigate and date
  useEffect(() => {
    openRef.current = { navigate, search }
  })

  // Make the map once: the loader's cities never change, and onMap only stores the map. React
  // runs this twice in development (StrictMode): the cleanup removes the first map.
  useEffect(() => {
    const container = containerRef.current!
    const colors = tokenColors(container)
    const start = viewFor(shownLevel.current, cities, container.clientWidth)
    const [[west, south], [east, north]] = boundsOf(cities.features)
    const map = new maplibregl.Map({
      container,
      style: {
        version: 8,
        sources: {},
        layers: [{ id: 'background', type: 'background', paint: { 'background-color': colors.background } }],
      },
      bounds: start.bounds,
      fitBoundsOptions: { padding: start.padding },
      maxBounds: [
        [west - PAN_MARGIN_DEG, south - PAN_MARGIN_DEG],
        [east + PAN_MARGIN_DEG, north + PAN_MARGIN_DEG],
      ],
      attributionControl: false,
      dragRotate: false,
      pitchWithRotate: false,
      touchPitch: false,
      renderWorldCopies: false,
    })
    map.touchZoomRotate.disableRotation()
    map.keyboard.disableRotation()
    const fader = hoverFader(map)
    const markers: Marker[] = []
    mapRef.current = map
    faderRef.current = fader

    map.on('load', () => {
      const open = shownLevel.current > 1 ? QC_PSGC : ''
      const opacity = shownLevel.current > 1 ? DIMMED_OPACITY : 1
      map.addSource(SOURCE, { type: 'geojson', data: cities, promoteId: 'psgc' })
      map.addLayer({
        id: LAYERS.fill,
        type: 'fill',
        source: SOURCE,
        filter: isNotOpen(open),
        paint: { 'fill-color': fillColor(colors), 'fill-opacity': opacity },
      })
      map.addLayer({
        id: LAYERS.line,
        type: 'line',
        source: SOURCE,
        filter: isNotOpen(open),
        layout: { 'line-join': 'round' },
        paint: { 'line-color': colors.line, 'line-width': LINE_WIDTH, 'line-opacity': opacity },
      })
      map.addLayer({
        id: LAYERS.openFill,
        type: 'fill',
        source: SOURCE,
        filter: isOpen(open),
        paint: { 'fill-color': fillColor(colors) },
      })
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
      setSpots(labelSpots)
      setLoaded(true)
    })

    // Level 1: hovering a city thickens its outline and shows its tooltip
    map.on('mousemove', LAYERS.fill, (event) => {
      const feature = event.features?.[0]
      if (shownLevel.current !== 1 || !feature) {
        return
      }
      const psgc = String(feature.properties.psgc)
      if (psgc !== hoveredRef.current) {
        if (hoveredRef.current) {
          fader.fade(hoveredRef.current, 0)
        }
        fader.fade(psgc, 1)
        hoveredRef.current = psgc
      }
      map.getCanvas().style.cursor = CITY_PATHS[psgc] ? 'pointer' : ''
      setPointer({ psgc, x: event.point.x, y: event.point.y, width: container.clientWidth, height: container.clientHeight })
    })
    map.on('mouseleave', LAYERS.fill, () => {
      if (hoveredRef.current) {
        fader.fade(hoveredRef.current, 0)
        hoveredRef.current = null
      }
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
    // A new map size: show the level's view again
    map.on('resize', () => {
      const view = viewFor(shownLevel.current, cities, container.clientWidth)
      map.fitBounds(view.bounds, { padding: view.padding, duration: 0 })
    })

    onMap(map)
    return () => {
      fader.stop()
      markers.forEach((marker) => marker.remove())
      map.remove()
      mapRef.current = null
      faderRef.current = null
      hoveredRef.current = null
      setSpots([])
      setLoaded(false)
      onMap(null)
    }
  }, [cities, onMap])

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
    map.setPaintProperty(LAYERS.fill, 'fill-opacity', opacity)
    map.setPaintProperty(LAYERS.line, 'line-opacity-transition', fade)
    map.setPaintProperty(LAYERS.line, 'line-opacity', opacity)
    // Not marked essential, so MapLibre skips the camera move when the reader asks for reduced motion
    const view = viewFor(level, cities, map.getContainer().clientWidth)
    map.fitBounds(view.bounds, { padding: view.padding, duration: CAMERA_MS, easing: easeInOut })
    if (level > 1 && hoveredRef.current) {
      faderRef.current?.fade(hoveredRef.current, 0)
      hoveredRef.current = null
      map.getCanvas().style.cursor = ''
      setPointer(null)
    }
  }, [level, loaded, cities])

  const model = week?.forecasts[forecast.map_model]
  const expected = model ? Math.round(model.mu) : null
  return (
    <div className="city-map" data-level={level}>
      <div ref={containerRef} className="city-map-canvas" />
      <p className="city-map-hint body-s">
        <Icon name="info" size={16} />
        Hover a city to check its data · click a city to open its forecast
      </p>
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
          style={tooltipPlace(pointer)}
        />
      )}
    </div>
  )
}

/** The tooltip's place: right of the pointer, or left of it near the map's right edge; kept inside the map. */
function tooltipPlace({ x, y, width, height }: Pointer): CSSProperties {
  const right = x + TOOLTIP_GAP + TOOLTIP_WIDTH <= width - TOOLTIP_GAP
  return {
    left: right ? x + TOOLTIP_GAP : x - TOOLTIP_GAP - TOOLTIP_WIDTH,
    top: Math.max(TOOLTIP_GAP, Math.min(y - TOOLTIP_GAP, height - TOOLTIP_TALLEST - TOOLTIP_GAP)),
    width: TOOLTIP_WIDTH,
  }
}

type CityTooltipProps = {
  city: CityProperties
  forecast: CityForecast
  week: ForecastWeek | undefined
  style: CSSProperties
}

/**
 * F4: the tooltip of the city under the pointer. Figma 1a: a city without data says so. Figma
 * 1b: a city with data shows its outbreak level and next week's expected cases. While the
 * forecasts are simulated it carries the amber badge (app check U2), which Figma's 1b lacks.
 */
function CityTooltip({ city, forecast, week, style }: CityTooltipProps) {
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
      <p className="city-map-tooltip-hint body-s">Click to open the forecast</p>
    </div>
  )
}
