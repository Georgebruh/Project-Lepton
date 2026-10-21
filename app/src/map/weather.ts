import type { MapEventType, Map as MapLibreMap } from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'
import { isSourceError } from './floodLayer.ts'
import { SLOTS } from './layerOrder.ts'
import { prefersReducedMotion } from './motion.ts'

/*
 * F13: weather on the map, like Zoom Earth, one layer at a time (the Layers panel, ?wx=):
 *   clouds     live: Himawari-9's infrared picture (JMA, through NASA GIBS), every 10 minutes,
 *              about 30 minutes behind; the last 3 hours of it;
 *   radar      live: RainViewer's rain radar, every 10 minutes; the past 2 hours;
 *   rain       live: NASA's IMERG rain rate (GIBS), every 30 minutes, about 6 hours behind; the
 *              last 6 hours of it;
 *   rain-day   IMERG's rain on the map's date, one UTC day (8 AM to 8 AM Philippine time);
 *   photo-day  NASA's VIIRS true-color photo of the map's date (one a day, early afternoon).
 * The live layers show now, not the map's date, and their timeline says so (WeatherTimeline).
 *
 * A layer is a list of frames. Each frame is a raster source and layer in the weather slot
 * (layerOrder.ts), named by its time, at opacity 0 but the one shown, so its tiles are loaded
 * before it is shown and the animation does not flicker. The frames are added one after another,
 * newest first: the newest shows at once, and RainViewer's free tiles stay under their 100
 * requests a minute. A live layer's list is fetched again every 10 minutes while the page is in
 * view: the frames already on the map stay, new ones are added, old ones go. The tiles are drawn
 * in the providers' own colors, so the legends (WEATHER_LEGENDS) use those colors too, not the
 * app's tokens.
 */

export const WEATHER = ['clouds', 'radar', 'rain', 'rain-day', 'photo-day'] as const
export type Weather = (typeof WEATHER)[number]

/** Whether a layer is live (now, animated) rather than the map's date (one picture). */
export function isLive(kind: Weather): boolean {
  return kind === 'clouds' || kind === 'radar' || kind === 'rain'
}

/** A frame: when its picture was taken (ms since 1970, UTC) and its tiles' address. */
export type Frame = { time: number; tiles: string }

/** How a layer is doing: none chosen, loading, shown, no picture for the map's date, or failed. */
export type WeatherStatus = 'off' | 'loading' | 'shown' | 'missing' | 'failed'

/** Each layer's name and caption in the Layers panel, and what the panel calls its picture. */
export const WEATHER_NAMES: Record<Weather, { label: string; caption: string; picture: string }> = {
  clouds: { label: 'Clouds · live', caption: 'Himawari-9 satellite, every 10 minutes', picture: 'the clouds' },
  radar: { label: 'Radar · live', caption: 'RainViewer, the past 2 hours', picture: 'the radar' },
  rain: { label: 'Rain · live', caption: 'NASA IMERG, every 30 minutes', picture: 'the rain' },
  'rain-day': { label: "Rain on the map's date", caption: 'NASA IMERG, one day', picture: "the day's rain" },
  'photo-day': {
    label: "Satellite photo on the map's date",
    caption: 'NASA VIIRS, one picture a day',
    picture: "the day's satellite photo",
  },
}

/** The sources' names, for the Layers panel's credits line (the map's own credits link them). */
export const WEATHER_CREDIT = 'Weather: NASA GIBS, RainViewer'

/**
 * How opaque each layer is over the map: LEPTON's outlines and the street map's names stay on
 * top. The infrared picture draws clear, warm ground dark grey, and the photo is opaque, so both
 * let the map show through more than the rain, which is clear where none falls.
 */
export const WEATHER_OPACITY: Record<Weather, number> = {
  clouds: 0.6,
  radar: 0.85,
  rain: 0.8,
  'rain-day': 0.8,
  'photo-day': 0.75,
}

/**
 * Each layer's legend, in the provider's colors: [color, position along the ramp in %]. Picked
 * from GIBS's colormaps (Clean_Longwave_Infrared_Window_Band: +50 °C to -90 °C; GPM_Precipitation_Rate:
 * 0.1 to 50 mm an hour, on a log scale) and RainViewer's Universal Blue table (10 to 65 dBZ).
 */
export const WEATHER_LEGENDS: Record<
  Weather,
  { title: string; stops: [string, number][]; ends: [string, string] | null; credit: string }
> = {
  clouds: {
    title: 'Clouds · cloud-top temperature',
    stops: [
      ['#131313', 0],
      ['#464646', 14],
      ['#7a7a7a', 29],
      ['#aeaeae', 43],
      ['#00f2f8', 50],
      ['#0073b2', 54],
      ['#000073', 57],
      ['#00ea0a', 64],
      ['#e6ff00', 71],
      ['#ff1a00', 79],
      ['#1a0000', 86],
      ['#e6e6e6', 93],
      ['#8c0d87', 100],
    ],
    ends: ['Clear or low cloud', 'Storm tops'],
    credit: 'Himawari-9 infrared (JMA) · NASA GIBS · live',
  },
  radar: {
    title: 'Rain radar',
    stops: [
      ['#cec087', 0],
      ['#88ddee', 9],
      ['#00a3e0', 18],
      ['#0077aa', 27],
      ['#005588', 36],
      ['#ffee00', 45],
      ['#ffaa00', 55],
      ['#ff4400', 64],
      ['#c10000', 73],
      ['#ffaaff', 82],
      ['#ff77ff', 91],
      ['#ffffff', 100],
    ],
    ends: ['Light', 'Heavy'],
    credit: 'RainViewer · past 2 hours · live',
  },
  rain: {
    title: 'Rain rate (mm per hour)',
    stops: rainStops(),
    ends: ['0.1', '50 or more'],
    credit: 'NASA IMERG via GIBS · live, about 6 hours behind',
  },
  'rain-day': {
    title: 'Rain rate (mm per hour) · one day',
    stops: rainStops(),
    ends: ['0.1', '50 or more'],
    credit: "NASA IMERG via GIBS · the map's date is a UTC day (8 AM to 8 AM PHT)",
  },
  'photo-day': {
    title: 'Satellite photo · true color',
    stops: [],
    ends: null,
    credit: 'NASA VIIRS via GIBS · one picture a day, taken early afternoon',
  },
}

/** IMERG's rain colors, 0.1 to 50 mm an hour, on a log scale (live and daily share them). */
function rainStops(): [string, number][] {
  return [
    ['#00764e', 0],
    ['#00971f', 11],
    ['#45c000', 26],
    ['#b8e100', 37],
    ['#ffb006', 48],
    ['#ff4730', 63],
    ['#ed0000', 74],
    ['#9c0000', 85],
    ['#3f0000', 100],
  ]
}

/** NASA GIBS's tiles in the web map projection. */
const GIBS = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best'

/** A GIBS layer: its name, its tile grid (how far in it goes), its picture type and its credit. */
type GibsLayer = { layer: string; matrix: string; maxzoom: number; ext: 'png' | 'jpg'; credit: string }

const GIBS_LINK = '<a href="https://earthdata.nasa.gov/gibs" target="_blank" rel="noopener">NASA GIBS</a>'
const IMERG: Omit<GibsLayer, 'layer'> = {
  matrix: 'GoogleMapsCompatible_Level6',
  maxzoom: 6,
  ext: 'png',
  credit: `Rain: NASA GPM IMERG via ${GIBS_LINK}`,
}
const GIBS_LAYERS: Record<Exclude<Weather, 'radar'>, GibsLayer> = {
  clouds: {
    layer: 'Himawari_AHI_Band13_Clean_Infrared',
    matrix: 'GoogleMapsCompatible_Level6',
    maxzoom: 6,
    ext: 'png',
    credit: `Clouds: Himawari-9 (JMA) via ${GIBS_LINK}`,
  },
  rain: { layer: 'IMERG_Precipitation_Rate_30min', ...IMERG },
  'rain-day': { layer: 'IMERG_Precipitation_Rate', ...IMERG },
  'photo-day': {
    layer: 'VIIRS_SNPP_CorrectedReflectance_TrueColor',
    matrix: 'GoogleMapsCompatible_Level9',
    maxzoom: 9,
    ext: 'jpg',
    credit: `Satellite photo: NASA VIIRS via ${GIBS_LINK}`,
  },
}

/** RainViewer's list of radar frames, and its tiles: 256 px, Universal Blue colors (2), smoothed, with snow (1_1). */
const RAINVIEWER = 'https://api.rainviewer.com/public/weather-maps.json'
const RADAR_TILE = '/256/{z}/{x}/{y}/2/1_1.png'
/** RainViewer's free tiles go to zoom 7. */
const RADAR_MAXZOOM = 7
const RADAR_CREDIT = 'Radar: <a href="https://www.rainviewer.com" target="_blank" rel="noopener">RainViewer</a>'

/** How far back the live layers look for frames, and how many of the newest they animate. */
const LIVE_LOOK_BACK_MS = { clouds: 6 * 3600_000, rain: 18 * 3600_000 }
const LIVE_FRAMES = { clouds: 18, rain: 12 }

/** Playback: 500 ms a frame and a 1.5 s pause on the newest (Figma notes); live frames fetched again every 10 minutes. */
const FRAME_MS = 500
const NEWEST_MS = 1500
const REFRESH_MS = 10 * 60_000

/** A time as GIBS writes it: "2026-10-21T09:10:00Z". */
function gibsTime(time: number): string {
  return new Date(time).toISOString().replace('.000Z', 'Z')
}

/** A GIBS step, "PT10M", "PT30M" or "P1D", in ms. */
function stepMs(step: string): number {
  const [, days, hours, minutes] = /^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$/.exec(step) ?? []
  return ((Number(days ?? 0) * 24 + Number(hours ?? 0)) * 60 + Number(minutes ?? 0)) * 60_000
}

/**
 * The times in one period of a GIBS time domain ("start/end/PT10M", or a single time) that fall
 * from `start` to `end` (ms). A period can begin years back, so only the window is stepped through.
 */
function periodTimes(period: string, start: number, end: number): number[] {
  const [from, to, step] = period.split('/')
  const first = Date.parse(from)
  const every = step ? stepMs(step) : 0
  if (!to || !(every > 0)) {
    return first >= start && first <= end ? [first] : []
  }
  const times: number[] = []
  const last = Math.min(Date.parse(to), end)
  for (let time = first + Math.max(0, Math.ceil((start - first) / every)) * every; time <= last; time += every) {
    times.push(time)
  }
  return times
}

/** The times GIBS has pictures of `gibs` for from `start` to `end` (ms), from its DescribeDomains call. */
async function gibsTimes(gibs: GibsLayer, start: number, end: number, signal: AbortSignal): Promise<number[]> {
  const window = `${gibsTime(start)}--${gibsTime(end)}`
  const res = await fetch(`${GIBS}/1.0.0/${gibs.layer}/default/${gibs.matrix}/all/${window}.xml`, { signal })
  if (!res.ok) {
    throw new Error(`GIBS ${res.status} ${res.statusText}`)
  }
  const domain = /<Domain>([^<]*)<\/Domain>/.exec(await res.text())?.[1] ?? ''
  return domain
    .split(',')
    .filter(Boolean)
    .flatMap((period) => periodTimes(period, start, end))
}

function gibsTiles(gibs: GibsLayer, time: string): string {
  return `${GIBS}/${gibs.layer}/default/${time}/${gibs.matrix}/{z}/{y}/{x}.${gibs.ext}`
}

/**
 * The frames whose pictures GIBS has made. Its list of times can name a picture before its tiles
 * are made (the newest Himawari frame, often), and MapLibre draws a missing tile as nothing, without
 * an error; so each frame's one tile of the whole world is asked for, headers only. A frame
 * whose answer does not come is left out, not the layer.
 */
async function madeFrames(frames: Frame[], signal: AbortSignal): Promise<Frame[]> {
  const made = await Promise.all(
    frames.map(async (frame) => {
      const world = frame.tiles.replace('{z}/{y}/{x}', '0/0/0')
      try {
        return (await fetch(world, { method: 'HEAD', signal })).ok
      } catch {
        return false
      }
    }),
  )
  return frames.filter((_, i) => made[i])
}

/** A layer's frames, oldest first: the newest live ones, or the map's date's one picture (none if NASA has none). */
async function framesFor(kind: Weather, day: string, signal: AbortSignal): Promise<Frame[]> {
  if (kind === 'radar') {
    const res = await fetch(RAINVIEWER, { signal })
    if (!res.ok) {
      throw new Error(`RainViewer ${res.status} ${res.statusText}`)
    }
    const maps = (await res.json()) as { host: string; radar: { past: { time: number; path: string }[] } }
    return maps.radar.past.map(({ time, path }) => ({ time: time * 1000, tiles: maps.host + path + RADAR_TILE }))
  }
  const gibs = GIBS_LAYERS[kind]
  if (kind === 'clouds' || kind === 'rain') {
    const end = Math.floor(Date.now() / 60_000) * 60_000 // whole minutes: GIBS takes no milliseconds
    const times = await gibsTimes(gibs, end - LIVE_LOOK_BACK_MS[kind], end, signal)
    // a few more than shown, in case the newest are not made yet
    const listed = times.slice(-LIVE_FRAMES[kind] - 3).map((time) => ({ time, tiles: gibsTiles(gibs, gibsTime(time)) }))
    return (await madeFrames(listed, signal)).slice(-LIVE_FRAMES[kind])
  }
  const start = Date.parse(`${day}T00:00:00Z`)
  const times = await gibsTimes(gibs, start, start + 24 * 3600_000 - 1000, signal)
  return madeFrames(times.includes(start) ? [{ time: start, tiles: gibsTiles(gibs, day) }] : [], signal)
}

/** A frame's source and layer (they share the id), named by its time, so a refresh keeps the frames it has. */
const PREFIX = 'weather-'
function frameId(frame: Frame): string {
  return `${PREFIX}${frame.time}`
}

/** Adds a frame's raster source and layer in the weather slot, at opacity 0 (its tiles load all the same). */
function addFrame(map: MapLibreMap, kind: Weather, frame: Frame) {
  const id = frameId(frame)
  map.addSource(id, {
    type: 'raster',
    tiles: [frame.tiles],
    tileSize: 256,
    maxzoom: kind === 'radar' ? RADAR_MAXZOOM : GIBS_LAYERS[kind].maxzoom,
    attribution: kind === 'radar' ? RADAR_CREDIT : GIBS_LAYERS[kind].credit,
  })
  map.addLayer(
    {
      id,
      type: 'raster',
      source: id,
      paint: { 'raster-opacity': 0, 'raster-opacity-transition': { duration: 0, delay: 0 }, 'raster-fade-duration': 0 },
    },
    SLOTS.weather,
  )
}

/** Shows the frame `shown` at `opacity` and the other frames at 0. */
function showFrame(map: MapLibreMap, frames: Frame[], shown: Frame | undefined, opacity: number) {
  for (const frame of frames) {
    const id = frameId(frame)
    if (map.getLayer(id)) {
      map.setPaintProperty(id, 'raster-opacity', frame === shown ? opacity : 0)
    }
  }
}

/** Removes the frames whose ids pass `which`, all of them by default (the map may be gone already, as the page leaves the map). */
function removeFrames(map: MapLibreMap, which: (id: string) => boolean = () => true) {
  try {
    for (const id of map.getLayersOrder().filter((layer) => layer.startsWith(PREFIX) && which(layer))) {
      map.removeLayer(id)
      map.removeSource(id)
    }
  } catch {
    // A removed map has nothing left to remove
  }
}

/** No frames: one list for every render, so the effects that depend on the frames do not rerun. */
const NO_FRAMES: Frame[] = []

/** What loading a layer reports: its frames, how many have their tiles, its status, and when its list came. */
type Run = { key: string; status: WeatherStatus; frames: Frame[]; loaded: number; fetched: number }

/**
 * Fetches `kind`'s frames and adds them to `map`, newest first, each once the one before has its
 * tiles where the map is now. A live layer's list is fetched again every REFRESH_MS while the
 * page is in view: frames already on the map stay, new ones are added, and those no longer listed
 * go. A frame whose tiles fail is dropped; if no frame has its tiles yet, the layer fails.
 * Reports to `report` as it goes; the returned function stops it and removes the frames.
 */
function loadWeather(map: MapLibreMap, kind: Weather, day: string, report: (news: Partial<Run>) => void): () => void {
  const controller = new AbortController()
  let frames: Frame[] = []
  const ready = new Set<string>() // the frames whose tiles are in
  let waiting: Frame | null = null // the frame being added, until its tiles are in
  let stopped = false

  const loaded = () => frames.filter((frame) => ready.has(frameId(frame))).length

  function addNext() {
    waiting = frames.findLast((frame) => !ready.has(frameId(frame))) ?? null
    if (waiting && !map.getLayer(frameId(waiting))) {
      addFrame(map, kind, waiting)
    }
  }
  // A frame's tiles are in once MapLibre has asked for them (it does as it draws, before 'render')
  // and all have come. One listener for every frame, so none is left over to count the next too soon
  function check() {
    if (!stopped && waiting && map.getSource(frameId(waiting)) && map.isSourceLoaded(frameId(waiting))) {
      ready.add(frameId(waiting))
      report({ loaded: loaded(), status: 'shown' })
      addNext()
    }
  }
  const onData = (event: MapEventType['sourcedata']) => {
    if (waiting && event.sourceId === frameId(waiting) && event.tile) {
      check()
    }
  }
  const onError = (event: MapEventType['error']) => {
    if (!waiting || !isSourceError(event, frameId(waiting))) {
      return
    }
    const failed = frameId(waiting)
    removeFrames(map, (id) => id === failed)
    frames = frames.filter((frame) => frameId(frame) !== failed)
    waiting = null
    if (loaded() === 0) {
      stop()
      report({ status: 'failed', frames: NO_FRAMES, loaded: 0 })
      return
    }
    report({ frames, loaded: loaded() })
    addNext()
  }

  async function fetchList() {
    try {
      const list = await framesFor(kind, day, controller.signal)
      if (stopped) {
        return
      }
      if (list.length === 0) {
        if (frames.length === 0) {
          report({ status: 'missing' })
        }
        return // a refresh that finds nothing keeps the frames it has
      }
      const listed = new Set(list.map(frameId))
      removeFrames(map, (id) => !listed.has(id))
      ready.forEach((id) => listed.has(id) || ready.delete(id))
      if (waiting && !listed.has(frameId(waiting))) {
        waiting = null
      }
      frames = list
      report({ frames, loaded: loaded(), fetched: Date.now() })
      if (!waiting) {
        addNext()
      }
    } catch {
      // A refresh that fails keeps the frames it has
      if (!stopped && frames.length === 0) {
        report({ status: 'failed' })
      }
    }
  }

  const timer = isLive(kind) ? setInterval(() => document.hidden || fetchList(), REFRESH_MS) : undefined
  function stop() {
    stopped = true
    controller.abort()
    clearInterval(timer)
    map.off('sourcedata', onData)
    map.off('error', onError)
    map.off('render', check)
    removeFrames(map)
  }
  map.on('sourcedata', onData)
  map.on('error', onError)
  map.on('render', check)
  fetchList()
  return stop
}

/** What MapLayout shows of the weather layer: the panel's status line, the legend and the timeline. */
export type WeatherView = {
  status: WeatherStatus
  /** The layer's frames, oldest first (empty while loading). */
  frames: Frame[]
  /** The frame shown. */
  index: number
  /** How many frames have their tiles. */
  loaded: number
  /** When the frames' list came (ms), for the frames' ages. */
  fetched: number
  playing: boolean
  play: (on: boolean) => void
  showFrame: (index: number) => void
  retry: () => void
}

/**
 * Shows the weather layer `kind` on `map` (null: none), for the map's date `day` if it is not
 * live. A live layer plays once all its frames are in, unless the reader asks for reduced motion
 * or has stepped through the frames themselves. When a refresh changes the list, the frame shown
 * stays (the newest stays the newest).
 */
export function useWeather(map: MapLibreMap | null, kind: Weather | null, day: string): WeatherView {
  const dayKey = kind && !isLive(kind) ? day : ''
  const [attempt, setAttempt] = useState(0)
  const [run, setRun] = useState<Run | null>(null)
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const readerStepped = useRef(false) // the reader paused or chose a frame of this layer: no autoplay
  const shownKind = useRef<Weather | null>(null)
  const shownFrames = useRef<Frame[]>(NO_FRAMES) // the frames the index counts in
  const key = `${kind}|${dayKey}|${attempt}`

  // Fetch the frames and add them to the map
  useEffect(() => {
    if (!map || !kind) {
      return
    }
    if (shownKind.current !== kind) {
      shownKind.current = kind
      readerStepped.current = false
    }
    shownFrames.current = NO_FRAMES
    const fresh: Run = { key, status: 'loading', frames: NO_FRAMES, loaded: 0, fetched: 0 }
    return loadWeather(map, kind, dayKey, (news) => {
      setRun((now) => ({ ...(now?.key === key ? now : fresh), ...news }))
      if (news.frames) {
        const before = shownFrames.current
        const after = news.frames
        shownFrames.current = after
        setIndex((i) => {
          const found = after.findIndex((frame) => frame.time === before[i]?.time)
          return i >= before.length - 1 || found < 0 ? after.length - 1 : found
        })
        if (before.length === 0) {
          setPlaying(false)
        }
      }
    })
  }, [map, kind, dayKey, key])

  const current = run?.key === key ? run : null
  const frames = current?.frames ?? NO_FRAMES
  const shown = Math.min(index, Math.max(frames.length - 1, 0))
  const allIn = frames.length > 1 && current?.loaded === frames.length

  // Autoplay once every frame is in
  useEffect(() => {
    if (allIn && !readerStepped.current && !prefersReducedMotion()) {
      setPlaying(true)
    }
  }, [allIn])

  // Show the frame chosen
  useEffect(() => {
    if (map && kind && frames.length > 0) {
      showFrame(map, frames, frames[shown], WEATHER_OPACITY[kind])
    }
  }, [map, kind, frames, shown, current?.loaded])

  // Play: the next frame every FRAME_MS, pausing on the newest
  useEffect(() => {
    if (!playing || frames.length < 2) {
      return
    }
    const last = frames.length - 1
    const timer = setTimeout(() => setIndex(shown >= last ? 0 : shown + 1), shown === last ? NEWEST_MS : FRAME_MS)
    return () => clearTimeout(timer)
  }, [playing, shown, frames])

  return {
    status: kind === null ? 'off' : (current?.status ?? 'loading'),
    frames,
    index: shown,
    loaded: current?.loaded ?? 0,
    fetched: current?.fetched ?? 0,
    playing,
    play: (on) => {
      readerStepped.current = !on
      setPlaying(on)
    },
    showFrame: (next) => {
      readerStepped.current = true
      setPlaying(false)
      setIndex(next)
    },
    retry: () => setAttempt((count) => count + 1),
  }
}

/** A frame's time in Philippine time, as the timeline writes it: "Tue 21 Oct, 08:10 PHT". */
const PHT = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Manila',
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})
export function phtTime(time: number): string {
  return `${PHT.format(time)} PHT`
}

/** How long before `now` a frame was taken: "20 minutes ago", "6 hours ago". */
export function ageOf(time: number, now: number): string {
  const minutes = Math.max(0, Math.round((now - time) / 60_000))
  if (minutes < 90) {
    return `${minutes} minute${minutes === 1 ? '' : 's'} ago`
  }
  return `${Math.round(minutes / 60)} hours ago`
}
