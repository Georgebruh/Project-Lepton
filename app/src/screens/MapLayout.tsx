import type { Map as MapLibreMap } from 'maplibre-gl'
import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { Outlet, useLoaderData, useSearchParams } from 'react-router'
import AppBar from '../components/AppBar.tsx'
import CityMap from '../map/CityMap.tsx'
import { chosenDate, dateRange, forecastFor } from '../map/forecast.ts'
import MapBreadcrumb from '../map/MapBreadcrumb.tsx'
import type { MapListHandle } from '../map/MapList.tsx'
import type { MapContext } from '../map/mapContext.ts'
import type { loadMapData } from '../map/mapData.ts'
import MapZoom from '../map/MapZoom.tsx'
import { CAMERA_MS, CROSSFADE_MS, EASE_CSS, HOVER_MS, PANEL_WIDTH, SHEET_SHARE } from '../map/motion.ts'
import OutbreakLegend from '../map/OutbreakLegend.tsx'
import { PLAN_PARAMS, useMapLevel, type MapLevel } from '../map/routes.ts'
import './MapLayout.css'

/** Each level's heading, for screen readers: the map has no visible page title. */
const HEADINGS: Record<MapLevel, string> = {
  1: 'Metro Manila: the chance of a leptospirosis outbreak next week',
  2: 'Quezon City: next week’s leptospirosis cases',
  3: 'Quezon City: the prophylaxis plan',
}

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
 */
export default function MapLayout() {
  const { cities, forecast } = useLoaderData<typeof loadMapData>()
  const level = useMapLevel()
  const [searchParams, setSearchParams] = useSearchParams()
  const [map, setMap] = useState<MapLibreMap | null>(null)
  const [legendSlot, setLegendSlot] = useState<HTMLElement | null>(null)
  const [overlay, setOverlay] = useState<HTMLElement | null>(null)
  const [listSlot, setListSlot] = useState<HTMLElement | null>(null)
  const controls = useRef<HTMLDivElement>(null)
  const panel = useRef<HTMLElement>(null)
  const cityList = useRef<MapListHandle>(null)
  const shownLevel = useRef(level)
  const date = chosenDate(forecast, searchParams.get('date'))
  const week = forecastFor(forecast, date)
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

  const context: MapContext = { cities, forecast, date, week, map, legendSlot, overlay, listSlot }
  return (
    <div className="map-layout" data-panel={level > 1 ? 'open' : 'closed'} style={MOTION}>
      <AppBar />
      <MapBreadcrumb level={level} date={date} first={first} last={last} onDateChange={changeDate} />
      <main className="map-layout-main">
        <h1 className="visually-hidden">{HEADINGS[level]}</h1>
        <CityMap
          cities={cities}
          forecast={forecast}
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
          {level < 3 && <OutbreakLegend levels={forecast.levels} simulated={forecast.simulated} />}
          {/* F5: a level's own legend goes here (the share of residents exposed, at level 3) */}
          <div ref={setLegendSlot} className="map-layout-legend" />
          <MapZoom map={map} />
        </div>
        {/* At level 1 the panel waits off-screen: inert, so the keyboard skips it */}
        <aside ref={panel} className="map-layout-panel" aria-label="Quezon City" inert={level === 1}>
          <Outlet context={context} />
        </aside>
      </main>
    </div>
  )
}
