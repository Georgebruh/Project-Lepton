import type { Map as MapLibreMap } from 'maplibre-gl'
import type { BaseMap } from '../map/basemap.ts'
import { DEFAULT_FLOOD, useFloodZones, type FloodPeriod } from '../map/floodLayer.ts'
import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { Link, Outlet, useLoaderData, useLocation, useNavigate, useSearchParams } from 'react-router'
import Logo from '../components/Logo.tsx'
import CityMap from '../map/CityMap.tsx'
import FloodLegend from '../map/FloodLegend.tsx'
import { chosenDate, dateRange, forecastFor, isSimulated, simulatedLabel } from '../map/forecast.ts'
import MapButton from '../map/MapButton.tsx'
import MapDataModes from '../map/MapDataModes.tsx'
import {
  baseOf,
  dataOf,
  floodOf,
  is3D,
  set3DParam,
  setBaseParam,
  setDataParam,
  setFloodParam,
  setWeatherParam,
  weatherOf,
} from '../map/layerParams.ts'
import MapLayers from '../map/MapLayers.tsx'
import MapSearch from '../map/MapSearch.tsx'
import type { MapContext } from '../map/mapContext.ts'
import { withSimulation, type DataMode, type MapData } from '../map/mapData.ts'
import MapTimeline from '../map/MapTimeline.tsx'
import MapZoom from '../map/MapZoom.tsx'
import {
  CAMERA_MS,
  CROSSFADE_MS,
  EASE_CSS,
  HOVER_MS,
  PANEL_MAX_WIDTH,
  PANEL_MIN_WIDTH,
  PANEL_SHARE,
  SHEET_SHARE,
  easeInOut,
} from '../map/motion.ts'
import OutbreakLegend from '../map/OutbreakLegend.tsx'
import { CITY_PATHS, MAP_PATHS, PLAN_PARAMS, QC_PSGC, levelSearch, useMapLevel, type MapLevel } from '../map/routes.ts'
import { TILT } from '../map/terrain.ts'
import { moveToLevel, viewFor } from '../map/view.ts'
import { WEATHER_NAMES, isLive, useWeather, type Weather } from '../map/weather.ts'
import WeatherLegend from '../map/WeatherLegend.tsx'
import WeatherTimeline from '../map/WeatherTimeline.tsx'
import './MapLayout.css'

/** Each level's heading, for screen readers: the map has no visible page title. */
const HEADINGS: Record<MapLevel, string> = {
  1: 'The Philippines: the chance of a leptospirosis outbreak next week',
  2: 'Quezon City: next week’s leptospirosis cases',
  3: 'Quezon City: the prophylaxis plan',
}

/** What the pin button above Zoom brings back into view at each level. The whole country at level 1. */
const LEVEL_PLACES: Record<MapLevel, string> = { 1: 'the Philippines', 2: 'Quezon City', 3: 'Quezon City' }

/** map/motion.ts's durations. */
const MOTION = {
  '--map-hover': `${HOVER_MS}ms`,
  '--map-camera': `${CAMERA_MS}ms`,
  '--map-crossfade': `${CROSSFADE_MS}ms`,
  '--map-ease': EASE_CSS,
  '--map-panel-width': `clamp(${PANEL_MIN_WIDTH}px, ${PANEL_SHARE * 100}vw, ${PANEL_MAX_WIDTH}px)`,
  '--map-sheet-share': `${SHEET_SHARE * 100}%`,
} as CSSProperties

/** The frame the map levels share. */
export default function MapLayout() {
  // The loader's own type (mapData.ts).
  const { cities, islands, forecast: realForecast, simulation, baseStyle } = useLoaderData() as MapData
  const level = useMapLevel()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { search } = useLocation()
  const [map, setMap] = useState<MapLibreMap | null>(null)
  const [legendSlot, setLegendSlot] = useState<HTMLElement | null>(null)
  const [overlay, setOverlay] = useState<HTMLElement | null>(null)
  const [listSlot, setListSlot] = useState<HTMLElement | null>(null)
  const [layersOpen, setLayersOpen] = useState(false)
  const [found, setFound] = useState<{ psgc: string } | null>(null) // The town the search last found
  const layersButton = useRef<HTMLButtonElement>(null)
  const controls = useRef<HTMLDivElement>(null)
  const topBar = useRef<HTMLDivElement>(null)
  const panel = useRef<HTMLElement>(null)
  const mapBox = useRef<HTMLElement>(null)
  const shownLevel = useRef(level)
  const mode: DataMode = simulation ? dataOf(searchParams) : 'real'
  const forecast = useMemo(() => withSimulation(realForecast, simulation, mode), [realForecast, simulation, mode])
  const date = chosenDate(forecast, searchParams.get('date'))
  const week = forecastFor(forecast, date)
  const base = baseOf(searchParams)
  // The prophylaxis plan opens in 3D of its own accord.
  const [plan3d, setPlan3d] = useState(level === 3)
  const [plan3dLevel, setPlan3dLevel] = useState(level)
  if (level !== plan3dLevel) {
    setPlan3dLevel(level)
    setPlan3d(level === 3)
  }
  const view3d = is3D(searchParams) || plan3d
  const flood = floodOf(searchParams)
  const [floodChoice, setFloodChoice] = useState<FloodPeriod>(flood ?? DEFAULT_FLOOD)
  if (flood !== null && flood !== floodChoice) {
    setFloodChoice(flood) // The switch brings back the map last shown, however the address came to name it
  }
  const { status: floodStatus, retry: retryFlood } = useFloodZones(map, flood)
  const floodShown = flood !== null && floodStatus !== 'failed'
  const weather = weatherOf(searchParams)
  const wx = useWeather(map, weather, date)
  const timeline = weather !== null && isLive(weather) && wx.frames.length > 1
  const { first, last } = dateRange(forecast)
  const realEnd = realForecast.weeks[realForecast.weeks.length - 1].end

  // The link or button that changed the level has gone.
  useEffect(() => {
    if (shownLevel.current === level) {
      return
    }
    shownLevel.current = level
    if (level === 1) {
      mapBox.current?.querySelector<HTMLElement>('canvas')?.focus({ preventScroll: true })
    } else {
      panel.current?.querySelector<HTMLElement>('h2')?.focus({ preventScroll: true })
    }
  }, [level])

  /** A new date replaces the address's (no new history entry); the page keeps its scroll. */
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

  /** Simulation or Real data replaces the address's (no new history entry). */
  function changeMode(next: DataMode) {
    setSearchParams((params) => setDataParam(params, next), { replace: true, preventScrollReset: true })
  }

  /** A base map chosen in the Layers panel replaces the address's (no new history entry). */
  function changeBase(next: BaseMap) {
    setSearchParams((params) => setBaseParam(params, next), { replace: true, preventScrollReset: true })
  }

  /** The 3D view turned on or off in the Layers panel replaces the address's (no new history entry). */
  function change3D(on: boolean) {
    if (!on) {
      setPlan3d(false)
    }
    setSearchParams((params) => set3DParam(params, on), { replace: true, preventScrollReset: true })
  }

  /** NOAH's map chosen in the Layers panel (null: none) replaces the address's (no new history entry). */
  function changeFlood(next: FloodPeriod | null) {
    setSearchParams((params) => setFloodParam(params, next), { replace: true, preventScrollReset: true })
  }

  /** The weather layer chosen in the Layers panel. */
  function changeWeather(next: Weather | null) {
    setSearchParams((params) => setWeatherParam(params, next), { replace: true, preventScrollReset: true })
  }

  /** Closing the Layers panel gives the keyboard back to its button. */
  function closeLayers() {
    setLayersOpen(false)
    layersButton.current?.focus()
  }

  /** The pin button: the camera goes back to the open level's view, as when the level opened. */
  function showLevel() {
    if (!map) {
      return
    }
    setFound(null)
    moveToLevel(map, viewFor(level, cities, map.getContainer(), controls.current, topBar.current), view3d ? TILT : 0, {
      duration: CAMERA_MS,
      easing: easeInOut,
    })
  }

  /** A place the search picked. */
  function pickPlace(psgc: string) {
    const path = CITY_PATHS[psgc]
    if (path && level > 1 && psgc === QC_PSGC) {
      showLevel()
    } else if (path) {
      navigate(path + levelSearch(2, search))
    } else {
      setFound({ psgc })
      if (level > 1) {
        navigate(MAP_PATHS[1] + levelSearch(1, search))
      }
    }
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
      <main ref={mapBox} className="map-layout-main">
        <h1 className="visually-hidden">{HEADINGS[level]}</h1>
        <CityMap
          cities={cities}
          islands={islands}
          forecast={forecast}
          baseStyle={baseStyle}
          base={base}
          view3d={view3d}
          week={week}
          level={level}
          onMap={setMap}
          controls={controls}
          topBar={topBar}
          found={found}
        />
        {/* A level's own tooltips go here, over the map (the barangays at level 3) */}
        <div ref={setOverlay} className="map-layout-overlay" />
        {/* The top left corner: the logo, a link home, and the search beside it. */}
        <div className="map-layout-top">
          <div className="map-layout-top-row">
            <Link to="/" className="map-layout-logo" aria-label="LEPTON, home page">
              <Logo />
            </Link>
            <MapSearch cities={cities} onPick={pickPlace} />
          </div>
          <div ref={setListSlot} className="map-layout-list-slot" />
        </div>
        {/* The top right corner: the data modes. */}
        <div ref={topBar} className="map-layout-modes">
          <MapDataModes mode={mode} onMode={changeMode} simulation={simulation} realEnd={realEnd} />
        </div>
        {/* Along the bottom, the timeline in the middle and the legends and buttons at the right */}
        <div ref={controls} className="map-layout-bottom">
          <div className="map-layout-bottom-grid">
            <div className="map-layout-timelines">
              {/* A live weather layer's timeline */}
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
              <MapTimeline date={date} first={first} last={last} forecast={forecast} onChange={changeDate} />
            </div>
            {/* The legends and the map buttons, side by side as one row */}
            <div className="map-layout-controls-row">
              {/* The legends, one above the other: the weather's and the flood zones' over the map's own */}
              <div className="map-layout-legends">
                {weather && (wx.status === 'loading' || wx.status === 'shown') && <WeatherLegend kind={weather} day={date} />}
                {floodShown && <FloodLegend period={flood} />}
                {level < 3 && (
                  <OutbreakLegend
                    levels={forecast.levels}
                    simulated={isSimulated(forecast, week) ? simulatedLabel(forecast) : null}
                  />
                )}
                {/* A level's own legend goes here (the share of residents exposed, at level 3) */}
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
