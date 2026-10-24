import type { Map as MapLibreMap } from 'maplibre-gl'

/* The prophylaxis plan's opening view. */

/** How fast the camera circles, in degrees a second: once round in two minutes. */
const DEGREES_PER_S = 3

/** How long the turn takes to reach that speed, in ms, so it starts gently. */
const SPEED_UP_MS = 2000

/** The most time one frame's step counts, in ms. */
const LONGEST_STEP_MS = 50

/** The event data the turn's own camera moves carry. */
const ORBIT = { orbit: true }

/** Whether a camera move must stop the turn: the reader's own, or one of the app's (view.ts). */
function takesTheMap(event: object): boolean {
  return ('originalEvent' in event && event.originalEvent !== undefined) || 'readerMove' in event || 'levelFit' in event
}

/** The share of full speed `ms` after the turn began: 0 to 1, easing in (smoothstep). */
function speedUp(ms: number): number {
  const t = Math.min(1, ms / SPEED_UP_MS)
  return t * t * (3 - 2 * t)
}

/** Starts circling the camera once the camera move under way has ended. */
export function orbit(map: MapLibreMap, onTurn: () => void): () => void {
  let frame = 0
  let began = 0
  let last = 0

  function turn(now: number) {
    const degrees = (DEGREES_PER_S * speedUp(now - began) * Math.min(now - last, LONGEST_STEP_MS)) / 1000
    last = now
    map.jumpTo({ bearing: map.getBearing() + degrees }, ORBIT)
    frame = requestAnimationFrame(turn)
  }

  function begin() {
    if (map.isMoving()) {
      return // Another move: wait for its end
    }
    map.off('moveend', begin)
    onTurn()
    began = last = performance.now()
    frame = requestAnimationFrame(turn)
  }

  function onMoveStart(event: object) {
    if (takesTheMap(event)) {
      stop()
    }
  }

  function stop() {
    cancelAnimationFrame(frame)
    map.off('moveend', begin)
    map.off('movestart', onMoveStart)
    map.off('mousedown', stop)
    map.off('touchstart', stop)
    map.off('wheel', stop)
  }

  map.on('movestart', onMoveStart)
  map.on('mousedown', stop)
  map.on('touchstart', stop)
  map.on('wheel', stop)
  if (map.isMoving()) {
    map.on('moveend', begin)
  } else {
    begin()
  }
  return stop
}
