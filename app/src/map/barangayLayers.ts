import type { ExpressionSpecification } from '@maplibre/maplibre-gl-style-spec'
import type { Map as MapLibreMap, MapLayerMouseEvent, MapMouseEvent } from 'maplibre-gl'
import { shapeMiddle, shapeParts, type LonLat } from '../exposed/nearest.ts'
import { CITY_LAYERS } from './cityLayers.ts'
import { featureFader, stagger } from './featureFades.ts'
import { SLOTS } from './layerOrder.ts'
import { CROSSFADE_MS, HOVER_MS, LINES_MS, RISE_MS, WAVE_MS, prefersReducedMotion } from './motion.ts'
import type { BarangayShapes } from './planData.ts'
import type { MapPointer } from './tooltip.ts'
import { tokenColor } from './tokens.ts'

/*
 * F5: Quezon City's barangays on the map, at level 3, the prophylaxis plan (Figma frames 3 and
 * 3a, and the notes "Map drill-down · design notes", node 58:447).
 *
 * The barangays are one GeoJSON source keyed on PSGC (promoteId), drawn by three layers that sit
 * between the open city's fill and its outline (cityLayers.ts; F13: the fills go in with the
 * city fills, over the street map's roads and under its names, layerOrder.ts): the fills, one color per class
 * (the share of each barangay's residents in zones the rain floods); white lines, 0.75 px; and a
 * dark 2 px outline for the barangay under the pointer.
 *
 * The motion, from the notes: the lines fade in (300 ms), then the fills rise in a wave from the
 * most exposed barangay to the least (600 ms) while the city's own fill fades out; Back plays it
 * in reverse. A new run (another lead time, or another storm) recolors the barangays in the same
 * wave. With reduced motion, each of these is a 150 ms crossfade. MapLibre does not animate a
 * feature-state change, so the rise and the recoloring are stepped frame by frame
 * (featureFades.ts). Each barangay's feature state: "rise" (0 to 1, its fill's opacity), "from"
 * and "to" (the class it leaves and the class it goes to), "t" (0 to 1, how far it has gone) and
 * "hover" (0 to 1, its dark outline).
 *
 * The plan's route component (MapProphylaxis) calls open() when the plan opens, show() with each
 * run and close() when it leaves. The layers outlive that component, so that close() can play
 * the reverse before removing them: barangayLayers(map) gives the same object for the same map
 * every time. F11: highlight() shows a barangay from the plan's list as the pointer would.
 * F13: setFillOpacity() lets the satellite or terrain base map show through the fills.
 *
 * F15: every barangay can be clicked (or tapped): onPick() hears which, and a click on the map
 * outside them, which closes the barangay's pop-up. select() keeps the dark outline on the
 * barangay whose pop-up is open (feature state "selected", 0 to 1, faded like "hover"), and the
 * pointer turns into a hand over the barangays.
 */

/** What the map shows of a run: each barangay's class and the order the wave reaches them. */
export type BarangayView = {
  /** Each barangay's class by PSGC: 0 to 4 (--color-data-ramp-1 to -5), or NO_DATA. */
  classes: Map<string, number>
  /** The barangays' PSGCs in the order the wave reaches them. */
  order: string[]
}

/** The class of a barangay on a date without a storm forecast: drawn bg/raised, like a city without data. */
export const NO_DATA = -1

/** The barangay under the pointer, and where the pointer is in the map, in px; F11: or the one the plan's list shows. */
export type BarangayPointer = MapPointer & { psgc: string; fromList?: boolean }

/** F15: the barangay a click (or a tap) picked, and the point of the map clicked, for its pop-up. */
export type BarangayPick = { psgc: string; at: LonLat }

const SOURCE = 'barangays'
const LAYERS = { fill: 'barangays-fill', line: 'barangays-line', hover: 'barangays-hover' }

/** Line widths in px, from Figma frames 3 and 3a: every barangay 0.75, the one under the pointer 2. */
const LINE = { rest: 0.75, hover: 2 }

/** The layer-wide paint values the plan fades: the lines, the other cities' outlines, the city's fill. */
type FadedPaint = 'line-opacity' | 'line-color' | 'fill-opacity'

const FROM: ExpressionSpecification = ['number', ['feature-state', 'from'], NO_DATA]
const TO: ExpressionSpecification = ['number', ['feature-state', 'to'], NO_DATA]
const T: ExpressionSpecification = ['number', ['feature-state', 't'], 1]
const RISE: ExpressionSpecification = ['number', ['feature-state', 'rise'], 0]
const HOVER: ExpressionSpecification = ['number', ['feature-state', 'hover'], 0]
const SELECTED: ExpressionSpecification = ['number', ['feature-state', 'selected'], 0]

/**
 * The colors the barangays paint with, read from tokens.css: MapLibre draws on a canvas and
 * cannot read CSS variables.
 */
function tokenColors(element: HTMLElement) {
  const color = (token: string) => tokenColor(element, token)
  return {
    ramp: [1, 2, 3, 4, 5].map((step) => color(`data-ramp-${step}`)),
    noData: color('bg-raised'),
    line: color('bg-surface'),
    hover: color('text-primary'),
    /** The other cities' outlines: dark at levels 1 and 2 (CityMap), light at level 3 (Figma frame 3). */
    cities: color('text-primary'),
    citiesDim: color('border-strong'),
  }
}

type Colors = ReturnType<typeof tokenColors>

/** A class's fill: the five ramp colors for classes 0 to 4, bg/raised for no data. */
function classColor(colors: Colors, value: ExpressionSpecification): ExpressionSpecification {
  const [one, two, three, four, five] = colors.ramp
  return ['match', value, 0, one, 1, two, 2, three, 3, four, 4, five, colors.noData]
}

export type BarangayLayers = ReturnType<typeof makeBarangayLayers>

const layersOfMap = new WeakMap<MapLibreMap, BarangayLayers>()

/** The barangay layers of a map: the same object for the same map every time, made on first use. */
export function barangayLayers(map: MapLibreMap): BarangayLayers {
  let layers = layersOfMap.get(map)
  if (!layers) {
    layers = makeBarangayLayers(map)
    layersOfMap.set(map, layers)
  }
  return layers
}

function makeBarangayLayers(map: MapLibreMap) {
  const colors = tokenColors(map.getContainer())
  const rise = new Map<string, number>() // each barangay's "rise", as last set
  const shown = new Map<string, number>() // each barangay's class, the one it shows or is going to
  const middles = new Map<string, LonLat>() // F11: a point inside each barangay, for its tooltip from the list
  let stage: 'closed' | 'open' | 'closing' = 'closed'
  let risen = false // whether the fills have risen, or are rising, since the plan opened
  let linesFrom = 0 // when the lines began to fade in (performance.now())
  let view: BarangayView | null = null // the run last shown
  let hover: ReturnType<typeof featureFader> | null = null
  let hovered: string | null = null
  let listener: ((pointer: BarangayPointer | null) => void) | null = null
  let selectFader: ReturnType<typeof featureFader> | null = null // F15: the open pop-up's barangay keeps its outline
  let selected: string | null = null
  let picker: ((pick: BarangayPick | null) => void) | null = null
  let stopRise = () => {}
  let stopRecolor = () => {}
  let riseTimer = 0
  let removeTimer = 0
  let removed = false
  let fillOpacity = 1 // F13: the most a fill shows, on the base map chosen (basemap.ts, DATA_OPACITY)

  // Once CityMap removes the map, nothing may touch it again
  map.once('remove', () => {
    removed = true
    stopMotion()
  })

  /** Moves a paint value the whole layer shares to `value` in `duration` ms: MapLibre animates that. */
  function paint(layer: string, property: FadedPaint, value: number | string, duration: number) {
    if (map.getLayer(layer)) {
      map.setPaintProperty(layer, `${property}-transition`, { duration, delay: 0 })
      map.setPaintProperty(layer, property, value)
    }
  }

  function setRise(psgc: string, value: number) {
    rise.set(psgc, value)
    map.setFeatureState({ source: SOURCE, id: psgc }, { rise: value })
  }

  /** Ends every wave, fade and timer where it is. */
  function stopMotion() {
    stopRise()
    stopRecolor()
    hover?.stop()
    selectFader?.stop()
    clearTimeout(riseTimer)
    clearTimeout(removeTimer)
  }

  /** Moves the dark outline to the barangay `psgc` (null: to none): the old one fades out as it fades in (150 ms). */
  function moveHover(psgc: string | null) {
    if (psgc === hovered) {
      return
    }
    if (hovered) {
      hover?.fade(hovered, 0)
    }
    if (psgc) {
      hover?.fade(psgc, 1)
    }
    hovered = psgc
  }

  /** Reports the barangay `psgc` at the point x, y of the map, in px, for its tooltip. */
  function report(psgc: string, x: number, y: number, fromList = false) {
    const { clientWidth: width, clientHeight: height } = map.getContainer()
    listener?.({ psgc, x, y, width, height, fromList })
  }

  /** The pointer over a barangay: thicken its outline (150 ms) and report it, for its tooltip. F15: a hand, since it can be clicked. */
  function onMove(event: MapLayerMouseEvent) {
    const feature = event.features?.[0]
    if (stage !== 'open' || !feature) {
      return
    }
    const psgc = String(feature.properties.psgc)
    moveHover(psgc)
    map.getCanvas().style.cursor = 'pointer'
    report(psgc, event.point.x, event.point.y)
  }

  function onLeave() {
    moveHover(null)
    map.getCanvas().style.cursor = ''
    listener?.(null)
  }

  /**
   * F15: a click (or a tap) on the map: the barangay under it is picked, for its pop-up; a click
   * outside the barangays picks none, which closes the pop-up. A drag is not a click (MapLibre).
   */
  function onClick(event: MapMouseEvent) {
    if (stage !== 'open') {
      return
    }
    const [feature] = map.queryRenderedFeatures(event.point, { layers: [LAYERS.fill] })
    picker?.(feature ? { psgc: String(feature.properties.psgc), at: [event.lngLat.lng, event.lngLat.lat] } : null)
  }

  /** F15: keeps the dark outline on the barangay `psgc` while its pop-up is open (null: on none), fading as a hover does. */
  function select(psgc: string | null) {
    const next = stage === 'open' ? psgc : null
    if (removed || next === selected) {
      return
    }
    if (selected) {
      selectFader?.fade(selected, 0)
    }
    if (next) {
      selectFader?.fade(next, 1)
    }
    selected = next
  }

  /** F15: a point inside the barangay `psgc`, near its middle, where a pop-up opened from the list points. */
  function middleOf(psgc: string): LonLat | undefined {
    return middles.get(psgc)
  }

  /**
   * F11: shows a barangay from the plan's list as the pointer would: its outline thickens and it
   * is reported at a point inside it, for its tooltip; null ends it.
   */
  function highlight(psgc: string | null) {
    const middle = psgc ? middles.get(psgc) : undefined
    if (stage !== 'open' || !psgc || !middle) {
      onLeave()
      return
    }
    moveHover(psgc)
    const { x, y } = map.project(middle)
    report(psgc, x, y, true)
  }

  /** Adds the source and the three layers, the lines and fills not yet shown. */
  function addLayers(shapes: BarangayShapes) {
    map.addSource(SOURCE, { type: 'geojson', data: shapes, promoteId: 'psgc' })
    for (const { properties, geometry } of shapes.features) {
      middles.set(properties.psgc, shapeMiddle(shapeParts(geometry)))
    }
    const below = CITY_LAYERS.openLine // the city's outline stays on top
    map.addLayer(
      {
        id: LAYERS.fill,
        type: 'fill',
        source: SOURCE,
        paint: {
          'fill-color': ['interpolate', ['linear'], T, 0, classColor(colors, FROM), 1, classColor(colors, TO)],
          'fill-opacity': ['*', RISE, fillOpacity],
        },
      },
      SLOTS.fills, // above the open city's fill, which fades out under them
    )
    map.addLayer(
      {
        id: LAYERS.line,
        type: 'line',
        source: SOURCE,
        layout: { 'line-join': 'round' },
        paint: { 'line-color': colors.line, 'line-width': LINE.rest, 'line-opacity': 0 },
      },
      below,
    )
    map.addLayer(
      {
        id: LAYERS.hover,
        type: 'line',
        source: SOURCE,
        layout: { 'line-join': 'round' },
        // F15: the barangay under the pointer, and the one whose pop-up is open
        paint: { 'line-color': colors.hover, 'line-width': LINE.hover, 'line-opacity': ['max', HOVER, SELECTED] },
      },
      below,
    )
    hover = featureFader(map, SOURCE, 'hover', HOVER_MS)
    selectFader = featureFader(map, SOURCE, 'selected', HOVER_MS)
    map.on('mousemove', LAYERS.fill, onMove)
    map.on('mouseleave', LAYERS.fill, onLeave)
    map.on('click', onClick)
  }

  /** Removes the barangays from the map, at the end of close(). */
  function removeLayers() {
    stopMotion()
    map.off('mousemove', LAYERS.fill, onMove)
    map.off('mouseleave', LAYERS.fill, onLeave)
    map.off('click', onClick)
    for (const id of [LAYERS.hover, LAYERS.line, LAYERS.fill]) {
      if (map.getLayer(id)) {
        map.removeLayer(id)
      }
    }
    if (map.getSource(SOURCE)) {
      map.removeSource(SOURCE)
    }
    rise.clear()
    shown.clear()
    middles.clear()
    hover = null
    hovered = null
    selectFader = null
    selected = null
    stage = 'closed'
  }

  /**
   * Opens the plan: adds the barangays (or keeps them, if they are still leaving) and fades their
   * lines in, while the other cities' outlines lighten (Figma frame 3). The fills wait for show().
   */
  function open(shapes: BarangayShapes) {
    if (removed || stage === 'open') {
      return
    }
    stopMotion()
    if (stage === 'closed') {
      addLayers(shapes)
    }
    stage = 'open'
    risen = false
    linesFrom = performance.now()
    const lines = prefersReducedMotion() ? CROSSFADE_MS : LINES_MS
    paint(LAYERS.line, 'line-opacity', 1, lines)
    paint(CITY_LAYERS.line, 'line-color', colors.citiesDim, lines)
  }

  /**
   * Shows a run on the barangays. The first after open() colors them, then, once the lines are
   * in, makes their fills rise in the wave while the city's fill fades out. A later run recolors
   * them in the same wave, each from the class it shows to its new one.
   */
  function show(next: BarangayView) {
    if (removed) {
      return
    }
    view = next
    if (stage !== 'open') {
      return // kept for the next open()
    }
    const quick = prefersReducedMotion()
    const wave = quick ? CROSSFADE_MS : WAVE_MS
    const each = quick ? CROSSFADE_MS : RISE_MS
    if (!risen) {
      risen = true
      for (const [psgc, value] of next.classes) {
        shown.set(psgc, value)
        map.setFeatureState({ source: SOURCE, id: psgc }, { from: value, to: value, t: 1 })
      }
      const wait = quick ? 0 : Math.max(0, linesFrom + LINES_MS - performance.now())
      riseTimer = window.setTimeout(() => {
        paint(CITY_LAYERS.openFill, 'fill-opacity', 0, wave)
        // The run shown by then, if another came while the lines faded in
        stopRise = stagger(view?.order ?? next.order, wave, each, (psgc, p) =>
          setRise(psgc, Math.max(rise.get(psgc) ?? 0, p)),
        )
      }, wait)
      return
    }
    stopRecolor()
    for (const [psgc, value] of next.classes) {
      map.setFeatureState({ source: SOURCE, id: psgc }, { from: shown.get(psgc) ?? value, to: value, t: 0 })
      shown.set(psgc, value)
    }
    stopRecolor = stagger(next.order, wave, each, (psgc, p) =>
      map.setFeatureState({ source: SOURCE, id: psgc }, { t: p }),
    )
  }

  /**
   * Closes the plan (Back): the fills sink in the reverse wave, the least exposed barangay first,
   * while the city's fill comes back; then the lines fade out and the barangays are removed.
   */
  function close() {
    if (removed || stage !== 'open') {
      return
    }
    stage = 'closing'
    risen = false
    stopRise()
    stopRecolor()
    clearTimeout(riseTimer)
    onLeave()
    if (selected) {
      selectFader?.fade(selected, 0) // F15: the pop-up's outline goes with the others
      selected = null
    }
    const quick = prefersReducedMotion()
    const wave = quick ? CROSSFADE_MS : WAVE_MS
    const lines = quick ? CROSSFADE_MS : LINES_MS
    function linesOut() {
      paint(LAYERS.line, 'line-opacity', 0, lines)
      paint(CITY_LAYERS.line, 'line-color', colors.cities, lines)
      removeTimer = window.setTimeout(removeLayers, lines)
    }
    paint(CITY_LAYERS.openFill, 'fill-opacity', fillOpacity, wave)
    const order = [...(view?.order ?? rise.keys())].reverse()
    const sink = (psgc: string, p: number) => setRise(psgc, Math.min(rise.get(psgc) ?? 0, 1 - p))
    // With reduced motion the lines fade out with the fills, in one crossfade
    stopRise = stagger(order, wave, quick ? CROSSFADE_MS : RISE_MS, sink, quick ? undefined : linesOut)
    if (quick) {
      linesOut()
    }
  }

  /** Tells `next` which barangay is under the pointer, and null when it leaves them; null stops telling. */
  function onHover(next: ((pointer: BarangayPointer | null) => void) | null) {
    listener = next
  }

  /** F15: tells `next` which barangay a click picks, and null for a click outside them; null stops telling. */
  function onPick(next: ((pick: BarangayPick | null) => void) | null) {
    picker = next
  }

  /**
   * F13: the most a fill shows (1 on the street map, less over imagery), now and for later opens.
   * The open city's fill takes it too, unless the barangays have risen over it.
   */
  function setFillOpacity(opacity: number) {
    fillOpacity = opacity
    if (removed) {
      return
    }
    if (map.getLayer(LAYERS.fill)) {
      map.setPaintProperty(LAYERS.fill, 'fill-opacity', ['*', RISE, opacity])
    }
    if (stage !== 'open' || !risen) {
      paint(CITY_LAYERS.openFill, 'fill-opacity', opacity, CROSSFADE_MS)
    }
  }

  return { open, show, close, onHover, highlight, setFillOpacity, onPick, select, middleOf }
}
