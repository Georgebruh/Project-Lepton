import type { Map as MapLibreMap } from 'maplibre-gl'
import { useOutletContext } from 'react-router'
import type { Cities, CityForecast, ForecastWeek } from './mapData.ts'

/** What MapLayout hands the open map level (its Outlet context). */
export type MapContext = {
  /** The files the /map route's loader fetched. */
  cities: Cities
  forecast: CityForecast
  /** The chosen date, YYYY-MM-DD: the address's ?date=, or the latest forecast day. */
  date: string
  /** The forecasts for the week after the chosen date, one per model; undefined if the backtest has none. */
  week: ForecastWeek | undefined
  /** The MapLibre map, for a level that draws its own layers; null until it has drawn the cities. */
  map: MapLibreMap | null
  /** Where a level puts its own legend, beside the zoom buttons (with createPortal); null until drawn. */
  legendSlot: HTMLElement | null
  /** A layer over the map for a level's own tooltips, in the map's px; null until drawn. */
  overlay: HTMLElement | null
  /** Where a level puts its own list for the keyboard, in the map's top left corner (with createPortal). */
  listSlot: HTMLElement | null
  /** Tells the layout which barangay's pop-up is open (null: none): NOAH's flood zones then show only inside it. */
  setOpenBarangay: (barangay: OpenBarangay | null) => void
}

/** A barangay whose pop-up is open, by its PSGC and the name the legend writes. */
export type OpenBarangay = { psgc: string; name: string }

/** The map context, in the component of a map level (MapMetroManila, MapQuezonCity, MapProphylaxis). */
export function useMapContext(): MapContext {
  return useOutletContext<MapContext>()
}
