import type { Map as MapLibreMap } from 'maplibre-gl'
import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { useLoaderData, useSearchParams } from 'react-router'
import Badge from '../components/Badge.tsx'
import { NO_DATA, barangayLayers, type BarangayPointer, type BarangayView } from '../map/barangayLayers.ts'
import BarangayTooltip from '../map/BarangayTooltip.tsx'
import ExposureLegend from '../map/ExposureLegend.tsx'
import { formatCount } from '../map/forecast.ts'
import { useMapContext } from '../map/mapContext.ts'
import { shortName } from '../map/mapData.ts'
import MapList, { type MapListItem } from '../map/MapList.tsx'
import { SHEET_BELOW, panelCover } from '../map/motion.ts'
import { PLAN_FLOOD, chosenRun, formatShare, joinRun, stormOn, waveOrder } from '../map/plan.ts'
import { loadRun, type BarangayRun, type BarangayShapes, type RunFile, type loadPlanData } from '../map/planData.ts'
import PlanPanel from '../map/PlanPanel.tsx'
import { PLAN_PARAMS, QC_PSGC } from '../map/routes.ts'
import { placeTooltip } from '../map/tooltip.ts'

/** The barangay tooltip's width in px (Figma 3a), and the most it is tall. */
const TOOLTIP_WIDTH = 264
const TOOLTIP_TALLEST = 230

/**
 * Map, level 3: the prophylaxis plan (route /map/quezon-city/prophylaxis), task F5, from the
 * Figma frames "3 Prophylaxis plan" (node 56:395) and its hover "3a" (57:741).
 *
 * The route's loader fetches storms.json, centers.json and the barangay shapes when the plan
 * first opens (map/planData.ts). The chosen date picks the storm (map/plan.ts, stormOn) and the
 * address's ?lead= its forecast, 1 to 3 days ahead; that forecast's barangay file is fetched when
 * it is first shown, and must join the shapes on PSGC, all 142. On a date without a storm, or
 * when the reader asks for "All storms" (?storms=all), the panel lists the storms instead. The
 * barangays are drawn on the layout's map (map/barangayLayers.ts), with the legend and the
 * tooltip in the layout's two boxes for them; the numbers fill the panel (map/PlanPanel.tsx).
 * Stock planning, not prescriptions.
 *
 * F11: the list of the 142 barangays in the map's top left corner (listSlot) reaches each from
 * the keyboard: the barangay reached thickens and shows its tooltip, as under the pointer.
 */
export default function MapProphylaxis() {
  const { cities, date, map, legendSlot, overlay, listSlot } = useMapContext()
  const { storms, centers, shapes } = useLoaderData<typeof loadPlanData>()
  const [searchParams, setSearchParams] = useSearchParams()
  const dateStorm = stormOn(storms.storms, date)
  const listing = searchParams.get(PLAN_PARAMS.list) === 'all'
  const storm = listing ? undefined : dateStorm
  const run = storm ? chosenRun(storm, searchParams.get(PLAN_PARAMS.lead)) : undefined
  const runFile = useRunFile(run?.file)
  const qc = cities.features.find((feature) => feature.properties.psgc === QC_PSGC)!.properties

  // The barangays of the run on the map: the one chosen, or until its file comes the one before
  const drawn = useMemo(() => (runFile ? joinRun(shapes, runFile) : undefined), [shapes, runFile])
  const hasStorm = storm !== undefined
  const view = useMemo(
    () => (hasStorm ? (drawn ? runView(drawn) : null) : noDataView(shapes)),
    [hasStorm, drawn, shapes],
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

  /** Another forecast: its lead time goes in the address (no new history entry), and the page keeps its scroll. */
  function changeLead(days: number) {
    setSearchParams(
      (params) => {
        params.set(PLAN_PARAMS.lead, String(days))
        return params
      },
      { replace: true, preventScrollReset: true },
    )
  }

  // The barangays' numbers in the run on the map, while a storm is shown; the tooltip and the list
  // (F11) say why there are none otherwise
  const numbers = hasStorm ? drawn : undefined
  const none = dateStorm ? 'Choose a storm to see its numbers' : 'No storm forecast for this date'

  return (
    <>
      <title>Prophylaxis plan · LEPTON</title>
      <PlanPanel
        city={shortName(qc)}
        storms={storms}
        centers={centers}
        storm={storm}
        run={run}
        date={date}
        stormOnDate={dateStorm !== undefined}
        barangays={shapes.features.length}
        onLead={changeLead}
      />
      {legendSlot &&
        storm &&
        createPortal(<ExposureLegend classes={storms.classes} flagShare={storms.flag_share} />, legendSlot)}
      {map &&
        listSlot &&
        createPortal(
          <MapList
            title="Barangays"
            items={barangayItems(shapes, numbers, none)}
            note={<p className="body-s">{numbers ? 'Most exposed first' : `${none}.`}</p>}
            instructions={
              numbers
                ? "The arrow keys or a barangay's first letters move through the list. Doses are stock planning, not prescriptions."
                : "The arrow keys or a barangay's first letters move through the list."
            }
            onShow={(psgc) => barangayLayers(map).highlight(psgc)}
          />,
          listSlot,
        )}
      {map && overlay && (
        <HoverTooltip map={map} overlay={overlay} shapes={shapes} barangays={numbers} note={`${none}.`} />
      )}
    </>
  )
}

/** A run on the map: each barangay's class, and the wave's order, the largest share exposed first. */
function runView(barangays: Map<string, BarangayRun>): BarangayView {
  const classes = new Map([...barangays].map(([psgc, barangay]) => [psgc, barangay.class]))
  return { classes, order: waveOrder(barangays.values()) }
}

/**
 * F11: the rows of the plan's list. With a storm's numbers, the most exposed share first (as the
 * wave), each with its share and the Flagged badge; a screen reader also hears its residents
 * exposed and its three units. Without them, the barangays by name, each saying `none`, why.
 */
function barangayItems(
  shapes: BarangayShapes,
  barangays: Map<string, BarangayRun> | undefined,
  none: string,
): MapListItem[] {
  const names = new Map(shapes.features.map(({ properties }) => [properties.psgc, properties.name]))
  if (!barangays) {
    return [...names]
      .map(([psgc, name]) => ({ id: psgc, name, words: none.toLowerCase() }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }
  return waveOrder(barangays.values()).map((psgc) => {
    const barangay = barangays.get(psgc)!
    const units = barangay.units[PLAN_FLOOD]
    const share = formatShare(barangay.share)
    return {
      id: psgc,
      name: names.get(psgc) ?? psgc,
      detail: (
        <>
          {barangay.flagged && <Badge tone="alert">Flagged</Badge>}
          <span className="data-m">{share}</span>
        </>
      ),
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

/**
 * A run's barangay file (`file` as storms.json names it), fetched when the run changes. Until it
 * comes, the file before it, so the map keeps its colors meanwhile; undefined at first. A file
 * that cannot be fetched stops with an error, which ErrorPage shows.
 */
function useRunFile(file: string | undefined): RunFile | undefined {
  const [loaded, setLoaded] = useState<RunFile>()
  const [failed, setFailed] = useState<unknown>(null)
  useEffect(() => {
    if (!file) {
      return
    }
    let current = true // false once the run changes again: a late file is dropped
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

type HoverTooltipProps = {
  map: MapLibreMap
  overlay: HTMLElement
  shapes: BarangayShapes
  /** The barangays' numbers in the run on the map; undefined while no storm is shown. */
  barangays: Map<string, BarangayRun> | undefined
  /** What the tooltip says while no storm is shown. */
  note: string
}

/**
 * The tooltip of the barangay under the pointer (Figma 3a), in the layout's box over the map. A
 * component of its own, so a move of the pointer redraws only the tooltip, not the panel.
 */
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
  // F11: on a phone the open list covers the map, and a tooltip would cover the list: the outline shows the barangay
  if (!pointer || (pointer.fromList && pointer.width < SHEET_BELOW)) {
    return null
  }
  // The panel covers the map's left side (F14), or on a phone its lower part (as the camera assumes, CityMap)
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
