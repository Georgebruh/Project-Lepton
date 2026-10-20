import type { LonLat } from './nearest.ts'

/**
 * F8: where the guide's distances start. The guide asks the phone for its position only when the
 * reader taps "Find the nearest health center" (the guide's notes in Figma); if the reader says
 * no, or the phone cannot tell, the reader types their barangay instead. The position stays in
 * the page's memory: never stored, never sent.
 */
export type Origin =
  /** Waiting for the reader's permission or for the phone's position. */
  | { kind: 'asking' }
  /** The phone's position, and how far off it may be, in metres. */
  | { kind: 'here'; point: LonLat; accuracyM: number }
  /** A barangay the reader picked: the distances start near its middle. */
  | { kind: 'barangay'; psgc: string }
  /** No position: the reader said no, the phone could not tell, or the browser cannot ask. */
  | { kind: 'no location'; why: NoLocation }

export type NoLocation = 'denied' | 'unavailable' | 'unsupported'

/** How long the phone may take to find its position before the guide offers the barangay search. */
const LOCATION_TIMEOUT_MS = 20_000

/** A position the phone found up to this long ago is good enough: the reader has not gone far. */
const LOCATION_MAX_AGE_MS = 60_000

/**
 * Asks the browser once for the phone's position and calls `done` with what it learns. Browsers
 * share a position only with pages served over https (or from localhost while testing); on
 * others the guide goes straight to the barangay search.
 */
export function askForLocation(done: (origin: Origin) => void): void {
  if (!window.isSecureContext || !('geolocation' in navigator)) {
    done({ kind: 'no location', why: 'unsupported' })
    return
  }
  navigator.geolocation.getCurrentPosition(
    ({ coords }) => done({ kind: 'here', point: [coords.longitude, coords.latitude], accuracyM: coords.accuracy }),
    (error) => done({ kind: 'no location', why: error.code === error.PERMISSION_DENIED ? 'denied' : 'unavailable' }),
    { enableHighAccuracy: true, timeout: LOCATION_TIMEOUT_MS, maximumAge: LOCATION_MAX_AGE_MS },
  )
}
