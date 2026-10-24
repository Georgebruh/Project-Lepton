import type { LonLat } from './nearest.ts'

/** Where the guide's distances start. */
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

/** Asks the browser once for the phone's position and calls `done` with what it learns. */
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
