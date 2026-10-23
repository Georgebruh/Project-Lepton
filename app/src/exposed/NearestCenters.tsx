import { useEffect, useMemo, useRef, useState, type ReactNode, type Ref } from 'react'
import Badge from '../components/Badge.tsx'
import Button from '../components/Button.tsx'
import Icon from '../components/Icon.tsx'
import BarangayPicker from './BarangayPicker.tsx'
import GuideMap from './GuideMap.tsx'
import GuideStep from './GuideStep.tsx'
import { useGuideData, type GuideBarangay, type GuideData } from './guideData.ts'
import type { Origin } from './location.ts'
import { directionsUrl, formatKm, insideRings, nearestPlaces, type LonLat } from './nearest.ts'
import './NearestCenters.css'

/** How many health centers the list shows (Figma: 3). */
const SHOWN_CENTERS = 3

/** A phone position less sure than this, in metres, gets a note under the list. */
const ROUGH_LOCATION_M = 250

/** The footer's note (Figma). */
const BRING_ID = 'Bring a valid ID if you have one. Consultation decides your medicine.'

/** Where the map's boundaries and the health centers come from (check U8). */
const CREDIT =
  'Boundaries: PSA and NAMRIA, via OCHA’s COD-AB on HDX (CC BY-IGO 3.0). Health centers: DOH National Health Facility Registry.'

/** Where the distances start. */
type Start = {
  point: LonLat
  /** The barangay the point lies in (or the one picked); none outside Quezon City. */
  barangay?: GuideBarangay
  /** The phone's position (true) or a picked barangay's middle (false). */
  here: boolean
  /** How far off the phone's position may be, in metres; 0 for a barangay. */
  accuracyM: number
}

/** Where the distances start, from the phone's position or a picked barangay; null before either. */
function startOf(origin: Origin, { barangays }: GuideData): Start | null {
  if (origin.kind === 'here') {
    const barangay = barangays.find(({ rings }) => insideRings(rings, origin.point))
    return { point: origin.point, barangay, here: true, accuracyM: origin.accuracyM }
  }
  if (origin.kind === 'barangay') {
    const barangay = barangays.find(({ psgc }) => psgc === origin.psgc)
    return barangay ? { point: barangay.middle, barangay, here: false, accuracyM: 0 } : null
  }
  return null
}

/** The note under the list: how the distances were measured, and what may make them less sure. */
function distanceNote(start: Start): string {
  if (!start.here) {
    return `Distances are in a straight line from the middle of ${start.barangay?.name}.`
  }
  const notes = ['Distances are in a straight line from where you are. LEPTON doesn’t send or keep your location.']
  if (start.accuracyM > ROUGH_LOCATION_M) {
    notes.push(`Your phone placed you to within about ${formatKm(start.accuracyM / 1000)}, so the order may differ.`)
  }
  if (!start.barangay) {
    notes.push('LEPTON lists only Quezon City’s health centers for now: outside Quezon City, ask your city’s health office.')
  }
  return notes.join(' ')
}

type NearestCentersProps = {
  /** Where the distances start: the phone's position, a picked barangay, or neither yet. */
  origin: Origin
  /** Asks the phone for its position again. */
  onUseLocation: () => void
  /** Starts the distances from a barangay, by its PSGC. */
  onPickBarangay: (psgc: string) => void
  onBack: () => void
  titleRef: Ref<HTMLHeadingElement>
}

/**
 * F8: step 3 of the guide, Figma frame "3 Nearest health centers" (39:411): the three health
 * centers nearest the reader by straight-line distance (nearest.ts), on a map and in a list, each
 * with a link that opens it in Google Maps. The distances start from the phone's position, asked
 * for only when the reader tapped "Find the nearest health center"; if the reader says no, or
 * the phone cannot tell, the reader types their barangay and the list starts from there. No
 * opening hours: Figma's are samples, and the guide shows hours only once the QC Health
 * Department confirms them.
 */
export default function NearestCenters({ origin, onUseLocation, onPickBarangay, onBack, titleRef }: NearestCentersProps) {
  const { data, failed, retry } = useGuideData()
  // The barangay search, opened by "Change" (or "Type your barangay" while the phone looks)
  const [changing, setChanging] = useState(false)
  const start = useMemo(() => (data ? startOf(origin, data) : null), [origin, data])
  const nearest = useMemo(
    () => (data && start ? nearestPlaces(data.centers, start.point, SHOWN_CENTERS) : []),
    [data, start],
  )
  const centerPoints = useMemo(() => nearest.map(({ lon, lat }): LonLat => [lon, lat]), [nearest])

  // After the reader picks a barangay, the keyboard moves to the new list's heading
  const listHeading = useRef<HTMLHeadingElement>(null)
  const focusList = useRef(false)
  useEffect(() => {
    if (focusList.current && listHeading.current) {
      focusList.current = false
      listHeading.current.focus()
    }
  })

  const searching = changing || origin.kind === 'no location'
  let body: ReactNode
  let button: ReactNode = null

  if (searching && data) {
    const reason = !changing && origin.kind === 'no location' ? origin.why : 'change'
    body = (
      <BarangayPicker
        barangays={data.barangays}
        reason={reason}
        onPick={(psgc) => {
          setChanging(false)
          focusList.current = true
          onPickBarangay(psgc)
        }}
        onUseLocation={
          reason === 'denied' || reason === 'unsupported'
            ? undefined
            : () => {
                setChanging(false)
                onUseLocation()
              }
        }
        onCancel={changing ? () => setChanging(false) : undefined}
      />
    )
  } else if (origin.kind === 'asking' && !searching) {
    body = (
      <>
        <LocationRow text="Finding your location…" action="Type your barangay" onAction={() => setChanging(true)} />
        <p className="nearest-centers-status body-m">
          If your phone asks, allow LEPTON to use your location. It stays on this phone: LEPTON doesn’t send or keep
          it.
        </p>
      </>
    )
  } else if (failed) {
    body = (
      <div className="nearest-centers-status">
        <p className="body-m">The list of health centers could not load. Check your connection, then try again.</p>
        <Button variant="secondary" onClick={retry}>
          Try again
        </Button>
      </div>
    )
  } else if (!data || !start) {
    body = <p className="nearest-centers-status body-m">Loading the health centers…</p>
  } else {
    const place = start.barangay?.name
    const where = start.here
      ? place
        ? `Near you · ${place}, Quezon City`
        : 'Near you · outside Quezon City'
      : `Near ${place}, Quezon City`
    const mapLabel = start.here
      ? `Map: where you are${place ? `, in ${place}` : ''}, and the ${nearest.length} nearest health centers, numbered as in the list.`
      : `Map: ${place} and the ${nearest.length} health centers nearest it, numbered as in the list.`
    body = (
      <>
        <LocationRow text={where} action="Change" onAction={() => setChanging(true)} />
        <GuideMap
          barangays={data.barangays}
          focus={start.barangay}
          you={start.here ? start.point : null}
          centers={centerPoints}
          label={mapLabel}
        />
        <section className="nearest-centers-results" aria-labelledby="nearest-centers-heading">
          <div className="nearest-centers-head">
            <h2 id="nearest-centers-heading" ref={listHeading} tabIndex={-1} className="nearest-centers-heading heading-s">
              {nearest.length} health centers near {start.here ? 'you' : place}
            </h2>
            <Badge>Straight-line distance</Badge>
          </div>
          <ol className="nearest-centers-list">
            {nearest.map((center, i) => (
              <li key={center.facilityCode} className="nearest-centers-row">
                <span className="nearest-centers-number label-ui-s" aria-hidden="true">
                  {i + 1}
                </span>
                <div className="nearest-centers-text">
                  <p className="nearest-centers-name label-ui">{center.name}</p>
                  <p className="nearest-centers-detail body-s">
                    {formatKm(center.km)} · Barangay {center.barangay}
                  </p>
                </div>
                <a
                  className="nearest-centers-directions"
                  href={directionsUrl([center.lon, center.lat])}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={`Open ${center.name} in Google Maps`}
                >
                  <Icon name="arrow-right" size={18} />
                </a>
              </li>
            ))}
          </ol>
          <p className="nearest-centers-note body-s">{distanceNote(start)}</p>
          <p className="nearest-centers-credit body-s">{CREDIT}</p>
        </section>
      </>
    )
    button = (
      <Button href={directionsUrl(centerPoints[0])} className="guide-step-button">
        Get directions to {nearest[0].name}
      </Button>
    )
  }

  const footer = (
    <>
      {button}
      <p className="nearest-centers-footnote body-s">{BRING_ID}</p>
    </>
  )
  return (
    <GuideStep step={3} title="Nearest health centers" onBack={onBack} titleRef={titleRef} footer={footer}>
      {body}
    </GuideStep>
  )
}

type LocationRowProps = {
  /** Where the list starts, or what the guide is doing. */
  text: string
  /** The button at the right: "Change", or "Type your barangay" while the phone looks. */
  action: string
  onAction: () => void
}

/** The line above the map, Figma "Location" (39:424): a pin, where the list starts, and Change. */
function LocationRow({ text, action, onAction }: LocationRowProps) {
  return (
    <div className="nearest-centers-location">
      <Icon name="pin" size={18} className="nearest-centers-pin" />
      <p className="nearest-centers-where label-ui" role="status">
        {text}
      </p>
      <button type="button" className="nearest-centers-change label-ui" onClick={onAction}>
        {action}
      </button>
    </div>
  )
}
