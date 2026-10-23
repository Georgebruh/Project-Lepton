import type { Map as MapLibreMap } from 'maplibre-gl'
import { useEffect, useId, useRef, useState } from 'react'
import Badge from '../components/Badge.tsx'
import Button from '../components/Button.tsx'
import Icon from '../components/Icon.tsx'
import type { LonLat } from '../exposed/nearest.ts'
import type { ReportInput } from '../report/reportContent.ts'
import { BarangayNumbers } from './BarangayTooltip.tsx'
import { panelCover } from './motion.ts'
import { forecastRuns, joinRun } from './plan.ts'
import { loadRun, type BarangayRun } from './planData.ts'
import { placeTooltip, type MapPointer } from './tooltip.ts'
import './BarangayTooltip.css'
import './BarangayPopup.css'

/** The pop-up's width in px, the tooltip's (Figma 3a), and the most it is tall: the tooltip's, with the report's button and its line. */
const POPUP_WIDTH = 264
const POPUP_TALLEST = 330

/** F15: the barangay whose pop-up is open, the point of the map it points at, and whether the plan's list opened it (Enter). */
export type PinnedBarangay = { psgc: string; at: LonLat; fromList: boolean }

/** What the report is made from besides the barangay: the plan's files, and the forecast and date the map shows. */
export type ReportRequest = Omit<ReportInput, 'leads' | 'psgc' | 'link' | 'made'>

/** What the report's button has done: nothing yet, making the PDF, saved it (the file's name), or failed. */
type ReportStatus = { state: 'idle' } | { state: 'making' } | { state: 'saved'; file: string } | { state: 'failed' }

const IDLE: ReportStatus = { state: 'idle' }

type BarangayPopupProps = {
  map: MapLibreMap
  pinned: PinnedBarangay
  /** The barangay's name. */
  name: string
  /** Its numbers in the run on the map; undefined while no storm is shown. */
  barangay: BarangayRun | undefined
  /** What it says while no storm is shown, e.g. "No storm forecast for this date." */
  note: string
  /** What its report needs; undefined while no storm is shown, and then it has no report. */
  report: ReportRequest | undefined
  /** Closes it; `hadFocus` says the keyboard was inside it, so the plan gives the keyboard back. */
  onClose: (hadFocus: boolean) => void
}

/**
 * F15: the pop-up a click (or a tap) on a barangay opens, or Enter in the plan's list: the
 * tooltip pinned where the barangay was clicked, with everything the tooltip shows (Figma 3a,
 * BarangayNumbers), a close button and Generate Report, which saves the barangay's report as a
 * PDF for health offices and LGUs (report/reportPdf.ts). It follows its point as the map moves,
 * kept beside the city panel (or above the sheet on a phone) as the tooltip is.
 *
 * A dialog that does not block the page: opened from the list it takes the keyboard, and the
 * close button or Escape gives it back to the list (or to the map). A click on the map outside
 * the barangays closes it too (barangayLayers' onPick). The report's code and the storm's other
 * forecasts are fetched as soon as it opens, so the PDF is ready when the button is pressed.
 */
export default function BarangayPopup({ map, pinned, name, barangay, note, report, onClose }: BarangayPopupProps) {
  const titleId = useId()
  const box = useRef<HTMLDivElement>(null)
  const pointer = useMapPoint(map, pinned.at)
  // The report's state for one forecast: another lead chip or storm starts afresh
  const key = report ? `${report.storm.storm}|${report.run.run}` : ''
  const [made, setMade] = useState<{ key: string; status: ReportStatus }>({ key, status: IDLE })
  const status = made.key === key ? made.status : IDLE

  /** Closes the pop-up, saying whether the keyboard was inside it. */
  function close() {
    onClose(box.current?.contains(document.activeElement) ?? false)
  }
  const closeRef = useRef(close)
  useEffect(() => {
    closeRef.current = close
  })

  // Opened from the list, the pop-up takes the keyboard
  useEffect(() => {
    if (pinned.fromList) {
      box.current?.focus({ preventScroll: true })
    }
  }, [pinned])

  // Escape closes it, wherever the keyboard is, unless a field or list there used the key first
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !event.defaultPrevented) {
        event.preventDefault()
        closeRef.current()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  // The report's code and files, fetched now so the PDF is ready on the button's press
  useEffect(() => {
    if (report) {
      reportParts(report).catch(() => {}) // fetched again, and its error shown, when the button is pressed
    }
  }, [report])

  /** Makes the barangay's report for the forecast on the map, and saves it as a PDF. */
  async function generate() {
    if (!report || status.state === 'making') {
      return
    }
    setMade({ key, status: { state: 'making' } })
    try {
      const [{ saveBarangayReport }, leads] = await reportParts(report)
      const file = saveBarangayReport({ ...report, leads, psgc: pinned.psgc, link: window.location.href, made: new Date() })
      setMade({ key, status: { state: 'saved', file } })
    } catch (error) {
      console.error(error)
      setMade({ key, status: { state: 'failed' } })
    }
  }

  // The panel covers the map's left side, or on a phone its lower part (as for the tooltip)
  const cover = panelCover(pointer.width, pointer.height)
  const shown = { ...pointer, height: pointer.height - cover.bottom }
  const style = placeTooltip(shown, POPUP_WIDTH, POPUP_TALLEST, pointer.width, cover.left)
  const words =
    status.state === 'making' ? 'Generating the report…' : status.state === 'saved' ? `Saved: ${status.file}` : ''
  return (
    <div
      ref={box}
      className="barangay-tooltip barangay-popup"
      style={style}
      role="dialog"
      aria-labelledby={titleId}
      tabIndex={-1}
    >
      <div className="barangay-tooltip-title">
        <p id={titleId} className="barangay-tooltip-name label-ui">
          {name}
        </p>
        {barangay?.flagged && <Badge tone="alert">Flagged</Badge>}
        <button type="button" className="barangay-popup-close" aria-label={`Close ${name}`} onClick={close}>
          <Icon name="close" size={16} />
        </button>
      </div>
      <BarangayNumbers barangay={barangay} note={note} />
      {report && (
        <Button icon="download" className="barangay-popup-report" onClick={generate}>
          Generate Report
        </Button>
      )}
      {words && (
        <p className="barangay-popup-status body-s" aria-hidden="true">
          {words}
        </p>
      )}
      {status.state === 'failed' && (
        <p className="barangay-popup-error body-s" role="alert">
          The report could not be made. Try again.
        </p>
      )}
      {/* Read out when the report is being made and when it is saved */}
      <p className="visually-hidden" aria-live="polite">
        {words}
      </p>
    </div>
  )
}

/**
 * Where a point of the map is, in the map's px, and the map's size, kept up to date as the map
 * moves (a drag, a zoom, the 3D view's turn) or changes size.
 */
function useMapPoint(map: MapLibreMap, [lon, lat]: LonLat): MapPointer {
  const [point, setPoint] = useState(() => mapPoint(map, lon, lat))
  useEffect(() => {
    const update = () => setPoint(mapPoint(map, lon, lat))
    update()
    map.on('move', update)
    map.on('resize', update)
    return () => {
      map.off('move', update)
      map.off('resize', update)
    }
  }, [map, lon, lat])
  return point
}

/** A point of the map in the map's px, with the map's size. */
function mapPoint(map: MapLibreMap, lon: number, lat: number): MapPointer {
  const { x, y } = map.project([lon, lat])
  const { clientWidth: width, clientHeight: height } = map.getContainer()
  return { x, y, width, height }
}

/**
 * What saving the report needs and the map may not have yet: the PDF module (with jsPDF, loaded
 * only now) and the storm's forecasts made 1 to 3 days ahead, each joined to the shapes. Fetched
 * once and kept (loadRun), so asking again is quick.
 */
function reportParts(report: ReportRequest) {
  return Promise.all([
    import('../report/reportPdf.ts'),
    Promise.all(
      forecastRuns(report.storm).map(async (run) => ({ run, barangays: joinRun(report.shapes, await loadRun(run.file)) })),
    ),
  ])
}
