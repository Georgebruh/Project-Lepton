import type { Map as MapLibreMap } from 'maplibre-gl'
import type { BaseMap } from '../map/basemap.ts'
import { DEFAULT_FLOOD, useFloodZones, type FloodPeriod } from '../map/floodLayer.ts'
import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { Outlet, useLoaderData, useSearchParams } from 'react-router'
import AppBar from '../components/AppBar.tsx'
import CityMap from '../map/CityMap.tsx'
import FloodLegend from '../map/FloodLegend.tsx'
import { chosenDate, dateRange, forecastFor } from '../map/forecast.ts'
import MapBreadcrumb from '../map/MapBreadcrumb.tsx'
import MapButton from '../map/MapButton.tsx'
import {
  baseOf,
  floodOf,
  is3D,
  set3DParam,
  setBaseParam,
  setFloodParam,
  setWeatherParam,
  weatherOf,
} from '../map/layerParams.ts'
import MapLayers from '../map/MapLayers.tsx'
import type { MapListHandle } from '../map/MapList.tsx'
import type { MapContext } from '../map/mapContext.ts'
import type { MapData } from '../map/mapData.ts'
import MapZoom from '../map/MapZoom.tsx'
import { CAMERA_MS, CROSSFADE_MS, EASE_CSS, HOVER_MS, PANEL_WIDTH, SHEET_SHARE, easeInOut } from '../map/motion.ts'
import OutbreakLegend from '../map/OutbreakLegend.tsx'
import { PLAN_PARAMS, useMapLevel, type MapLevel } from '../map/routes.ts'
import { TILT } from '../map/terrain.ts'
import { moveToLevel, viewFor } from '../map/view.ts'
import { WEATHER_NAMES, isLive, useWeather, type Weather } from '../map/weather.ts'
import WeatherLegend from '../map/WeatherLegend.tsx'
import WeatherTimeline from '../map/WeatherTimeline.tsx'
import './MapLayout.css'

/** Each level's heading, for screen readers: the map has no visible page title. */
const HEADINGS: Record<MapLevel, string> = {
  1: 'Metro Manila: the chance of a leptospirosis outbreak next week',
  2: 'Quezon City: next week’s leptospirosis cases',
  3: 'Quezon City: the prophylaxis plan',
}

/** F13: what the pin button above Zoom brings back into view at each level. */
const LEVEL_PLACES: Record<MapLevel, string> = { 1: 'Metro Manila', 2: 'Quezon City', 3: 'Quezon City' }

/** map/motion.ts's durations and curve, as the CSS variables MapLayout.css and the map's CSS use. */
const MOTION = {
  '--map-hover': `${HOVER_MS}ms`,
  '--map-camera': `${CAMERA_MS}ms`,
  '--map-crossfade': `${CROSSFADE_MS}ms`,
  '--map-ease': EASE_CSS,
  '--map-panel-width': `${PANEL_WIDTH}px`,
  '--map-sheet-share': `${SHEET_SHARE * 100}%`,
} as CSSProperties

/**
 * The frame the three map levels share (routes /map, /map/quezon-city and
 * /map/quezon-city/prophylaxis), from the Figma map drill-down (section 53:267): the app bar,
 * the breadcrumb bar with the date picker, the one map with its legend and zoom buttons, and
 * the panel on the right. The map stays on screen while the level changes, so the drill-down
 * can animate (task F4; the motion is in map/motion.ts). The open level fills the panel
 * (<Outlet />), which slides in when a city opens.
 *
 * The chosen date is kept in the address (?date=2024-10-22), so a link opens the same week;
 * without one, the map shows the latest forecast.
 *
 * F5: the prophylaxis plan (level 3) draws its barangays on the same map, and puts its own
 * legend and tooltip in two empty boxes here, which the context hands it (legendSlot, overlay).
 *
 * F11: on a phone (below 600 px, motion.ts's SHEET_BELOW) the panel is a sheet that slides up
 * over the map's lower 55% instead of in from the right, so the map stays in sight above it. The
 * map's top left corner holds a list that reaches every city (level 1) or barangay (level 3)
 * from the keyboard; the plan puts its list there through the context (listSlot).
 *
 * F13: the map lies on a street map of the whole world, and the reader may pan away from Metro
 * Manila; the pin button above Zoom brings the open level back into view. The Layers button
 * opens the Layers panel (map/MapLayers.tsx); its choices live in the address (?base=, ?flood=,
 * ?view=3d, ?wx=, map/layerParams.ts), so a link opens the same map. NOAH's flood zones
 * (map/floodLayer.ts) and the weather layer (map/weather.ts) bring their legends, which stand
 * above the map's own; a live weather layer brings its timeline, at the bottom left.
 */
export default function MapLayout() {
  // The loader's own type (mapData.ts): React Router's serialized form of a MapLibre style is
  // too deep for TypeScript, and with no server nothing is serialized
  const { cities, forecast, baseStyle } = useLoaderData() as MapData
  const level = useMapLevel()
  const [searchParams, setSearchParams] = useSearchParams()
  const [map, setMap] = useState<MapLibreMap | null>(null)
  const [legendSlot, setLegendSlot] = useState<HTMLElement | null>(null)
  const [overlay, setOverlay] = useState<HTMLElement | null>(null)
  const [listSlot, setListSlot] = useState<HTMLElement | null>(null)
  const [layersOpen, setLayersOpen] = useState(false)
  const layersButton = useRef<HTMLButtonElement>(null)
  const controls = useRef<HTMLDivElement>(null)
  const panel = useRef<HTMLElement>(null)
  const cityList = useRef<MapListHandle>(null)
  const shownLevel = useRef(level)
  const date = chosenDate(forecast, searchParams.get('date'))
  const week = forecastFor(forecast, date)
  const base = baseOf(searchParams)
  const view3d = is3D(searchParams)
  const flood = floodOf(searchParams)
  const [floodChoice, setFloodChoice] = useState<FloodPeriod>(flood ?? DEFAULT_FLOOD)
  if (flood !== null && flood !== floodChoice) {
    setFloodChoice(flood) // the switch brings back the map last shown, however the address came to name it
  }
  const { status: floodStatus, retry: retryFlood } = useFloodZones(map, flood)
  const floodShown = flood !== null && floodStatus !== 'failed'
  const weather = weatherOf(searchParams)
  const wx = useWeather(map, weather, date)
  const timeline = weather !== null && isLive(weather) && wx.frames.length > 1
  const { first, last } = dateRange(forecast)

  // F11: the link or button that changed the level has gone, or slid away with the panel, so the
  // keyboard moves to where the new level starts: the panel's heading, or, back at Metro Manila,
  // the list of cities. Not on the first view, where the keyboard starts at the top as usual.
  useEffect(() => {
    if (shownLevel.current === level) {
      return
    }
    shownLevel.current = level
    if (level === 1) {
      cityList.current?.focus()
    } else {
      panel.current?.querySelector<HTMLElement>('h2')?.focus({ preventScroll: true })
    }
  }, [level])

  /**
   * A new date replaces the address's (no new history entry); the page keeps its scroll. A date
   * the reader picks also ends a storm opened from the plan's list (F5): there is no other date
   * to go back to.
   */
  function changeDate(day: string) {
    setSearchParams(
      (params) => {
        params.set('date', day)
        params.delete(PLAN_PARAMS.from)
        params.delete(PLAN_PARAMS.list)
        return params
      },
      { replace: true, preventScrollReset: true },
    )
  }

  /** F13: a base map chosen in the Layers panel replaces the address's (no new history entry). */
  function changeBase(next: BaseMap) {
    setSearchParams((params) => setBaseParam(params, next), { replace: true, preventScrollReset: true })
  }

  /** F13: the 3D view turned on or off in the Layers panel replaces the address's (no new history entry). */
  function change3D(on: boolean) {
    setSearchParams((params) => set3DParam(params, on), { replace: true, preventScrollReset: true })
  }

  /** F13: NOAH's map chosen in the Layers panel (null: none) replaces the address's (no new history entry). */
  function changeFlood(next: FloodPeriod | null) {
    setSearchParams((params) => setFloodParam(params, next), { replace: true, preventScrollReset: true })
  }

  /** F13: the weather layer chosen in the Layers panel (null: none) replaces the address's (no new history entry). */
  function changeWeather(next: Weather | null) {
    setSearchParams((params) => setWeatherParam(params, next), { replace: true, preventScrollReset: true })
  }

  /** F13: closing the Layers panel gives the keyboard back to its button. */
  function closeLayers() {
    setLayersOpen(false)
    layersButton.current?.focus()
  }

  /** F13: the pin button: the camera goes back to the open level's view, as when the level opened. */
  function showLevel() {
    if (!map) {
      return
    }
    moveToLevel(map, viewFor(level, cities, map.getContainer(), controls.current), view3d ? TILT : 0, {
      duration: CAMERA_MS,
      easing: easeInOut,
    })
  }

  const context: MapContext = { cities, forecast, date, week, map, legendSlot, overlay, listSlot }
  return (
    <div
      className="map-layout"
      data-panel={level > 1 ? 'open' : 'closed'}
      data-layers={layersOpen ? 'open' : undefined}
      data-flood={floodShown ? 'on' : undefined}
      data-timeline={timeline ? 'on' : undefined}
      style={MOTION}
    >
      <AppBar />
      <MapBreadcrumb level={level} date={date} first={first} last={last} onDateChange={changeDate} />
      <main className="map-layout-main">
        <h1 className="visually-hidden">{HEADINGS[level]}</h1>
        <CityMap
          cities={cities}
          forecast={forecast}
          baseStyle={baseStyle}
          base={base}
          view3d={view3d}
          week={week}
          level={level}
          onMap={setMap}
          controls={controls}
          listRef={cityList}
          onListSlot={setListSlot}
        />
        {/* F5: a level's own tooltips go here, over the map (the barangays at level 3) */}
        <div ref={setOverlay} className="map-layout-overlay" />
        <div ref={controls} className="map-layout-controls">
          {/* F13: a live weather layer's timeline, at the bottom left */}
          {timeline && (
            <WeatherTimeline
              label={WEATHER_NAMES[weather].label}
              frames={wx.frames}
              index={wx.index}
              now={wx.now}
              playing={wx.playing}
              onPlay={wx.play}
              onFrame={wx.showFrame}
            />
          )}
          {/* F13: the legends and the map buttons, side by side as one row */}
          <div className="map-layout-controls-row">
            {/* F13: the legends, one above the other: the weather's and the flood zones' over the map's own */}
            <div className="map-layout-legends">
              {weather && (wx.status === 'loading' || wx.status === 'shown') && <WeatherLegend kind={weather} day={date} />}
              {floodShown && <FloodLegend period={flood} />}
              {level < 3 && <OutbreakLegend levels={forecast.levels} simulated={forecast.simulated} />}
              {/* F5: a level's own legend goes here (the share of residents exposed, at level 3) */}
              <div ref={setLegendSlot} className="map-layout-legend" />
            </div>
            <div className="map-layout-buttons">
              <MapButton icon="pin" label={`Back to ${LEVEL_PLACES[level]}`} onClick={showLevel} />
              <MapButton
                ref={layersButton}
                icon="layers"
                label="Map layers"
                open={layersOpen}
                controls="map-layers"
                onClick={() => setLayersOpen((open) => !open)}
              />
              <MapZoom map={map} />
            </div>
          </div>
        </div>
        {/* At level 1 the panel waits off-screen: inert, so the keyboard skips it */}
        <aside ref={panel} className="map-layout-panel" aria-label="Quezon City" inert={level === 1}>
          <Outlet context={context} />
        </aside>
        {layersOpen && (
          <MapLayers
            id="map-layers"
            base={base}
            onBase={changeBase}
            view3d={view3d}
            on3D={change3D}
            hasStreetMap={baseStyle !== null}
            flood={flood}
            floodChoice={floodChoice}
            floodStatus={floodStatus}
            onFlood={changeFlood}
            onFloodRetry={retryFlood}
            weather={weather}
            weatherStatus={wx.status}
            day={date}
            onWeather={changeWeather}
            onWeatherRetry={wx.retry}
            onClose={closeLayers}
          />
        )}
      </main>
    </div>
  )
}
