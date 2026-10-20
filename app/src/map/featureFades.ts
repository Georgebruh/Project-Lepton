import type { Map as MapLibreMap } from 'maplibre-gl'

/*
 * F4 and F5: animations of the map's feature states. MapLibre redraws a feature-state change at
 * once: its paint transitions skip any value that differs from feature to feature. So a fade of
 * one feature (a hover, F4) or of many in turn (the barangays' wave, F5) is played here, a step
 * each frame.
 */

/**
 * Fades one feature state, `key`, of a source's features between 0 and 1, taking `duration` ms
 * for the whole way (F4's hoverFader). fade(id, 1) starts a feature's fade in, fade(id, 0) its
 * fade out; a fade under way turns round from where it is.
 */
export function featureFader(map: MapLibreMap, source: string, key: string, duration: number) {
  const now = new Map<string, number>() // each feature's value at this frame
  const goal = new Map<string, number>() // where each fading feature is going
  let frame = 0
  let last = 0
  function step(time: number) {
    const move = last ? (time - last) / duration : 0
    last = time
    for (const [id, target] of goal) {
      const from = now.get(id) ?? 0
      const next = target > from ? Math.min(target, from + move) : Math.max(target, from - move)
      now.set(id, next)
      map.setFeatureState({ source, id }, { [key]: next })
      if (next === target) {
        goal.delete(id)
      }
    }
    frame = goal.size ? requestAnimationFrame(step) : 0
    if (!frame) {
      last = 0
    }
  }
  return {
    fade(id: string, target: number) {
      goal.set(id, target)
      if (!frame) {
        frame = requestAnimationFrame(step)
      }
    },
    /** Ends every fade where it is: call it before the map or the source is removed. */
    stop() {
      cancelAnimationFrame(frame)
      frame = 0
      last = 0
      goal.clear()
    },
  }
}

/**
 * Plays a wave over features (F5): each id in `order` moves from 0 to 1 in `each` ms, and the
 * starts are spread evenly over the first `total - each` ms, so the first starts at once and the
 * last ends at `total`. Every frame, step(id, p) gets each moving feature's new p (0 to 1), and
 * done() is called once the last has reached 1. Returns stop(), which ends the wave where it is.
 *
 * With `total` equal to `each`, every feature moves at once: a crossfade, for reduced motion.
 */
export function stagger(
  order: string[],
  total: number,
  each: number,
  step: (id: string, p: number) => void,
  done?: () => void,
): () => void {
  const apart = order.length > 1 ? Math.max(0, total - each) / (order.length - 1) : 0
  let first = 0 // the first feature still moving: every one before it has reached 1
  let start: number | undefined
  let frame = requestAnimationFrame(tick)
  function tick(time: number) {
    start ??= time
    const elapsed = time - start
    for (let i = first; i < order.length; i++) {
      const begins = i * apart
      if (begins > elapsed) {
        break // this feature and the ones after it have not started yet
      }
      const p = each > 0 ? Math.min(1, (elapsed - begins) / each) : 1
      step(order[i], p)
      if (p === 1 && i === first) {
        first += 1
      }
    }
    if (first < order.length) {
      frame = requestAnimationFrame(tick)
    } else {
      frame = 0
      done?.()
    }
  }
  return () => {
    cancelAnimationFrame(frame)
    frame = 0
  }
}
