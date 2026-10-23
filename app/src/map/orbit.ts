import type { Map as MapLibreMap } from 'maplibre-gl'

/*
 * F14: the prophylaxis plan's opening view. In 3D, the camera circles slowly about the middle of
 * the map left in sight (Quezon City, beside the panel) until the reader takes the map: a click
 * or a touch on it, the wheel, a key, or the zoom or pin buttons. It does not start again until
 * the plan opens again. CityMap starts it, never with reduced motion.
 *
 * Each frame turns the camera a little with jumpTo, which would cancel any other camera move under
 * way, so the turn ends as soon as one starts: the reader's (it comes with their event) or the
 * app's (view.ts marks them READER_MOVE or LEVEL_FIT). Its own moves carry ORBIT.
 */

/** How fast the camera circles, in degrees a second: once round in two minutes. */
const DEGREES_PER_S = 3

/** How long the turn takes to reach that speed, in ms, so it starts gently. */
const SPEED_UP_MS = 2000

/**
 * The most time one frame's step counts, in ms. The first seconds of 3D can hold the page for up
 * to 0.8 s (the terrain's first tiles and shaders, measured 23 October 2026); after such a pause
 * the camera carries on from where it was instead of jumping ahead.
 */
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

/**
 * Starts circling the camera once the camera move under way (the plan's tilt) has ended, and
 * calls `onTurn` as it starts. Returns the function that stops it; it also stops by itself when
 * the reader takes the map.
 */
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
      return // another move: wait for its end
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
