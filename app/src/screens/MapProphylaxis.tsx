import type { Map as MapLibreMap } from 'maplibre-gl'
import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useLoaderData, useSearchParams } from 'react-router'
import { NO_DATA, barangayLayers, type BarangayPointer, type BarangayView } from '../map/barangayLayers.ts'
import BarangayPopup, { type PinnedBarangay, type ReportRequest } from '../map/BarangayPopup.tsx'
import BarangayTooltip from '../map/BarangayTooltip.tsx'
import ExposureLegend from '../map/ExposureLegend.tsx'
import { formatCount } from '../map/forecast.ts'
import { useMapContext } from '../map/mapContext.ts'
import { shortName } from '../map/mapData.ts'
import MapList, { type MapListHandle, type MapListItem } from '../map/MapList.tsx'
import { SHEET_BELOW, panelCover } from '../map/motion.ts'
import { PLAN_FLOOD, chosenRun, dayOn, formatShare, joinRun, stormOn, waveOrder, withDayNeeds } from '../map/plan.ts'
import {
  loadDays,
  loadRun,
  type BarangayRun,
  type BarangayShapes,
  type DaysFile,
  type RunFile,
  type loadPlanData,
} from '../map/planData.ts'
import PlanPanel from '../map/PlanPanel.tsx'
import { PLAN_PARAMS, QC_PSGC } from '../map/routes.ts'
import { placeTooltip } from '../map/tooltip.ts'

/** The barangay tooltip's width in px, and the most it is tall. */
const TOOLTIP_WIDTH = 264
const TOOLTIP_TALLEST = 230

/** Map, level 3: the prophylaxis plan. */
export default function MapProphylaxis() {
  const { cities, forecast, date, week, map, legendSlot, overlay } = useMapContext()
  const { storms, centers, shapes } = useLoaderData<typeof loadPlanData>()
  const [searchParams, setSearchParams] = useSearchParams()
  const [pinned, setPinned] = useState<PinnedBarangay | null>(null)
  const list = useRef<MapListHandle>(null)
  const dateStorm = stormOn(storms.storms, date)
  const days = useDaysFile(Number(date.slice(0, 4)))
  const dateDay = days ? dayOn(days, date) : undefined
  const storm = dateStorm ?? dateDay
  // The date's own plan is on its way: its year's file has not come yet (null: it could not be fetched)
  const loading = storm === undefined && days === undefined
  const run = storm ? chosenRun(storm, searchParams.get(PLAN_PARAMS.lead)) : undefined
  const runFile = useRunFile(run?.file)
  const qc = cities.features.find((feature) => feature.properties.psgc === QC_PSGC)!.properties
  // A day's plan reads its runs' needs per health center as a storm's are read, from centers.json
  const planCenters = useMemo(
    () => (days && storm && storm === dateDay ? withDayNeeds(centers, days, storm) : centers),
    [centers, days, storm, dateDay],
  )

  // The barangays of the run on the map: the one chosen, or until its file comes the one before
  const drawn = useMemo(() => (runFile ? joinRun(shapes, runFile) : undefined), [shapes, runFile])
  const hasStorm = storm !== undefined
  const view = useMemo(
    () => (hasStorm ? (drawn ? runView(drawn) : null) : loading ? null : noDataView(shapes)),
    [hasStorm, drawn, loading, shapes],
  )

  // The barangays join the map when the plan opens, and leave it, in reverse, when it closes
  useEffect(() => {
    if (!map) {
      return
    }
    const layers = barangayLayers(map)
    layers.open(shapes)
    return () => layers.close()
  }, [map, shapes])

  // Each run, once its file has come, rises (or recolors) in the wave
  useEffect(() => {
    if (map && view) {
      barangayLayers(map).show(view)
    }
  }, [map, view])

  // A click on a barangay opens its pop-up where it was clicked; a click elsewhere on the map closes it
  useEffect(() => {
    if (!map) {
      return
    }
    const layers = barangayLayers(map)
    layers.onPick((pick) => setPinned(pick && { ...pick, fromList: false }))
    return () => layers.onPick(null)
  }, [map])

  // The open pop-up's barangay keeps its dark outline
  useEffect(() => {
    if (map) {
      barangayLayers(map).select(pinned?.psgc ?? null)
    }
  }, [map, pinned])

  /** Enter (or a click) on a row of the list opens the barangay's pop-up, pointing near its middle. */
  function openFromList(psgc: string) {
    const at = map ? barangayLayers(map).middleOf(psgc) : undefined
    if (at) {
      setPinned({ psgc, at, fromList: true })
    }
  }

  /** Closes the pop-up; if the keyboard was in it. */
  function closePopup(hadFocus: boolean) {
    const fromList = pinned?.fromList
    setPinned(null)
    if (hadFocus) {
      if (fromList) {
        list.current?.focus()
      } else {
        map?.getCanvas().focus({ preventScroll: true })
      }
    }
  }

  /** Another forecast: its lead time goes in the address. */
  function changeLead(days: number) {
    setSearchParams(
      (params) => {
        params.set(PLAN_PARAMS.lead, String(days))
        return params
      },
      { replace: true, preventScrollReset: true },
    )
  }

  // The barangays' numbers in the run on the map, while a storm is shown.
  const numbers = hasStorm ? drawn : undefined
  // What the tooltip and the pop-up say without numbers: the plan, or its run's file, is on its way
  const none = loading || hasStorm ? 'Loading the plan for this date' : 'No plan for this date'

  // What a barangay's report is made from, while a storm's forecast is shown
  const report: ReportRequest | undefined = useMemo(
    () => (storm && run ? { storms, centers: planCenters, shapes, storm, run, forecast, week, date } : undefined),
    [storms, planCenters, shapes, storm, run, forecast, week, date],
  )

  return (
    <>
      <PlanPanel
        city={shortName(qc)}
        storms={storms}
        centers={planCenters}
        storm={storm}
        run={run}
        loading={loading}
        barangays={shapes.features.length}
        list={
          // The panel's Barangays view, most exposed first
          map && (
            <MapList
              ref={list}
              title="Barangays"
              items={barangayItems(shapes, numbers, none)}
              instructions={
                "The arrow keys or a barangay's first letters move through the list, and Enter opens the barangay " +
                'with its report. Doses are stock planning, not prescriptions.'
              }
              onShow={(psgc) => barangayLayers(map).highlight(psgc)}
              onOpen={openFromList}
            />
          )
        }
        onLead={changeLead}
      />
      {legendSlot &&
        storm &&
        createPortal(<ExposureLegend classes={storms.classes} flagShare={storms.flag_share} />, legendSlot)}
      {map && overlay && !pinned && (
        <HoverTooltip map={map} overlay={overlay} shapes={shapes} barangays={numbers} note={`${none}.`} />
      )}
      {map &&
        overlay &&
        pinned &&
        createPortal(
          <BarangayPopup
            key={pinned.psgc}
            map={map}
            pinned={pinned}
            name={shapes.features.find((feature) => feature.properties.psgc === pinned.psgc)?.properties.name ?? pinned.psgc}
            barangay={numbers?.get(pinned.psgc)}
            note={`${none}.`}
            report={report}
            onClose={closePopup}
          />,
          overlay,
        )}
    </>
  )
}

/** A run on the map: each barangay's class, and the wave's order, the largest share exposed first. */
function runView(barangays: Map<string, BarangayRun>): BarangayView {
  const classes = new Map([...barangays].map(([psgc, barangay]) => [psgc, barangay.class]))
  return { classes, order: waveOrder(barangays.values()) }
}

/** The rows of the plan's list. */
function barangayItems(
  shapes: BarangayShapes,
  barangays: Map<string, BarangayRun> | undefined,
  none: string,
): MapListItem[] {
  const names = new Map(shapes.features.map(({ properties }) => [properties.psgc, properties.name]))
  if (!barangays) {
    return [...names]
      .map(([psgc, name]) => ({ id: psgc, name, words: none.toLowerCase(), opens: true }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }
  return waveOrder(barangays.values()).map((psgc) => {
    const barangay = barangays.get(psgc)!
    const units = barangay.units[PLAN_FLOOD]
    const share = formatShare(barangay.share)
    return {
      id: psgc,
      name: names.get(psgc) ?? psgc,
      opens: true,
      // The barangay's color on the map (class 0 is the ramp's first color); the two darkest are flagged
      marker: <span className="plan-swatch" style={{ background: `var(--color-data-ramp-${barangay.class + 1})` }} />,
      detail: <span className="data-m">{share}</span>,
      words:
        `${share} of residents exposed, ${formatCount(barangay.exposed)} of ${formatCount(barangay.pop_2024)}` +
        `${barangay.flagged ? ', flagged' : ''}; ${formatCount(units.doxy100)} doxycycline 100 mg capsules, ` +
        `${formatCount(units.courses)} children's courses, ${formatCount(units.amox500)} amoxicillin 500 mg tablets`,
    }
  })
}

/** The map on a date without a storm forecast: every barangay without data, in PSGC order. */
function noDataView(shapes: BarangayShapes): BarangayView {
  const order = shapes.features.map((feature) => feature.properties.psgc).sort()
  return { classes: new Map(order.map((psgc) => [psgc, NO_DATA])), order }
}

/** A run's barangay file (`file` as storms.json names it), fetched when the run changes. */
function useRunFile(file: string | undefined): RunFile | undefined {
  const [loaded, setLoaded] = useState<RunFile>()
  const [failed, setFailed] = useState<unknown>(null)
  useEffect(() => {
    if (!file) {
      return
    }
    let current = true // False once the run changes again: a late file is dropped
    loadRun(file).then(
      (run) => {
        if (current) {
          setLoaded(run)
        }
      },
      (error: unknown) => {
        if (current) {
          setFailed(error)
        }
      },
    )
    return () => {
      current = false
    }
  }, [file])
  if (failed) {
    throw failed
  }
  return loaded
}

/** The daily plans of `year` (days/<year>.json), fetched when the date first reaches that year. */
function useDaysFile(year: number): DaysFile | null | undefined {
  const [loaded, setLoaded] = useState<{ year: number; file: DaysFile | null }>()
  useEffect(() => {
    let current = true // False once the year changes again: a late file is dropped
    loadDays(year).then(
      (file) => {
        if (current) {
          setLoaded({ year, file })
        }
      },
      () => {
        if (current) {
          setLoaded({ year, file: null })
        }
      },
    )
    return () => {
      current = false
    }
  }, [year])
  return loaded?.year === year ? loaded.file : undefined
}

type HoverTooltipProps = {
  map: MapLibreMap
  overlay: HTMLElement
  shapes: BarangayShapes
  /** The barangays' numbers in the run on the map; undefined while no storm is shown. */
  barangays: Map<string, BarangayRun> | undefined
  /** What the tooltip says while no storm is shown. */
  note: string
}

/** The tooltip of the barangay under the pointer, in the layout's box over the map. */
function HoverTooltip({ map, overlay, shapes, barangays, note }: HoverTooltipProps) {
  const [pointer, setPointer] = useState<BarangayPointer | null>(null)
  const names = useMemo(
    () => new Map(shapes.features.map(({ properties }) => [properties.psgc, properties.name])),
    [shapes],
  )
  useEffect(() => {
    const layers = barangayLayers(map)
    layers.onHover(setPointer)
    return () => {
      layers.onHover(null)
      setPointer(null)
    }
  }, [map])
  // On a phone the open list covers the map, and a tooltip would cover the list.
  if (!pointer || (pointer.fromList && pointer.width < SHEET_BELOW)) {
    return null
  }
  // The panel covers the map's left side, or on a phone its lower part (as the camera assumes, CityMap)
  const cover = panelCover(pointer.width, pointer.height)
  const shown = { ...pointer, height: pointer.height - cover.bottom }
  return createPortal(
    <BarangayTooltip
      key={pointer.psgc}
      name={names.get(pointer.psgc) ?? pointer.psgc}
      barangay={barangays?.get(pointer.psgc)}
      note={note}
      style={placeTooltip(shown, TOOLTIP_WIDTH, TOOLTIP_TALLEST, pointer.width, cover.left)}
    />,
    overlay,
  )
}
