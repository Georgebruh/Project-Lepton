import type { ExpressionSpecification } from '@maplibre/maplibre-gl-style-spec'
import type { Map as MapLibreMap, MapLayerMouseEvent } from 'maplibre-gl'
import { CITY_LAYERS } from './cityLayers.ts'
import { featureFader, stagger } from './featureFades.ts'
import { CROSSFADE_MS, HOVER_MS, LINES_MS, RISE_MS, WAVE_MS, prefersReducedMotion } from './motion.ts'
import type { BarangayShapes } from './planData.ts'
import type { MapPointer } from './tooltip.ts'

/*
 * F5: Quezon City's barangays on the map, at level 3, the prophylaxis plan (Figma frames 3 and
 * 3a, and the notes "Map drill-down · design notes", node 58:447).
 *
 * The barangays are one GeoJSON source keyed on PSGC (promoteId), drawn by three layers that sit
 * between the open city's fill and its outline (cityLayers.ts): the fills, one color per class
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
 * every time.
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

/** The barangay under the pointer, and where the pointer is in the map, in px. */
export type BarangayPointer = MapPointer & { psgc: string }

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

/**
 * The colors the barangays paint with, read from tokens.css: MapLibre draws on a canvas and
 * cannot read CSS variables.
 */
function tokenColors(element: HTMLElement) {
  const style = getComputedStyle(element)
  const color = (token: string) => style.getPropertyValue(`--color-${token}`).trim()
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
  let stage: 'closed' | 'open' | 'closing' = 'closed'
  let risen = false // whether the fills have risen, or are rising, since the plan opened
  let linesFrom = 0 // when the lines began to fade in (performance.now())
  let view: BarangayView | null = null // the run last shown
  let hover: ReturnType<typeof featureFader> | null = null
  let hovered: string | null = null
  let listener: ((pointer: BarangayPointer | null) => void) | null = null
  let stopRise = () => {}
  let stopRecolor = () => {}
  let riseTimer = 0
  let removeTimer = 0
  let removed = false

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
    clearTimeout(riseTimer)
    clearTimeout(removeTimer)
  }

  /** The pointer over a barangay: thicken its outline (150 ms) and report it, for its tooltip. */
  function onMove(event: MapLayerMouseEvent) {
    const feature = event.features?.[0]
    if (stage !== 'open' || !feature) {
      return
    }
    const psgc = String(feature.properties.psgc)
    if (psgc !== hovered) {
      if (hovered) {
        hover?.fade(hovered, 0)
      }
      hover?.fade(psgc, 1)
      hovered = psgc
    }
    const { clientWidth: width, clientHeight: height } = map.getContainer()
    listener?.({ psgc, x: event.point.x, y: event.point.y, width, height })
  }

  function onLeave() {
    if (hovered) {
      hover?.fade(hovered, 0)
      hovered = null
    }
    listener?.(null)
  }

  /** Adds the source and the three layers, the lines and fills not yet shown. */
  function addLayers(shapes: BarangayShapes) {
    map.addSource(SOURCE, { type: 'geojson', data: shapes, promoteId: 'psgc' })
    const below = CITY_LAYERS.openLine // the city's outline stays on top
    map.addLayer(
      {
        id: LAYERS.fill,
        type: 'fill',
        source: SOURCE,
        paint: {
          'fill-color': ['interpolate', ['linear'], T, 0, classColor(colors, FROM), 1, classColor(colors, TO)],
          'fill-opacity': RISE,
        },
      },
      below,
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
        paint: { 'line-color': colors.hover, 'line-width': LINE.hover, 'line-opacity': HOVER },
      },
      below,
    )
    hover = featureFader(map, SOURCE, 'hover', HOVER_MS)
    map.on('mousemove', LAYERS.fill, onMove)
    map.on('mouseleave', LAYERS.fill, onLeave)
  }

  /** Removes the barangays from the map, at the end of close(). */
  function removeLayers() {
    stopMotion()
    map.off('mousemove', LAYERS.fill, onMove)
    map.off('mouseleave', LAYERS.fill, onLeave)
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
    hover = null
    hovered = null
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
    const quick = prefersReducedMotion()
    const wave = quick ? CROSSFADE_MS : WAVE_MS
    const lines = quick ? CROSSFADE_MS : LINES_MS
    function linesOut() {
      paint(LAYERS.line, 'line-opacity', 0, lines)
      paint(CITY_LAYERS.line, 'line-color', colors.cities, lines)
      removeTimer = window.setTimeout(removeLayers, lines)
    }
    paint(CITY_LAYERS.openFill, 'fill-opacity', 1, wave)
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

  return { open, show, close, onHover }
}
