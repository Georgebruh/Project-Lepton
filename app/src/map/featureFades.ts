import type { Map as MapLibreMap } from 'maplibre-gl'

/* Animations of the map's feature states. */

/** Fades one feature state. */
export function featureFader(map: MapLibreMap, source: string, key: string, duration: number) {
  const now = new Map<string, number>() // Each feature's value at this frame
  const goal = new Map<string, number>() // Where each fading feature is going
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

/** Plays a wave over features. */
export function stagger(
  order: string[],
  total: number,
  each: number,
  step: (id: string, p: number) => void,
  done?: () => void,
): () => void {
  const apart = order.length > 1 ? Math.max(0, total - each) / (order.length - 1) : 0
  let first = 0 // The first feature still moving: every one before it has reached 1
  let start: number | undefined
  let frame = requestAnimationFrame(tick)
  function tick(time: number) {
    start ??= time
    const elapsed = time - start
    for (let i = first; i < order.length; i++) {
      const begins = i * apart
      if (begins > elapsed) {
        break // This feature and the ones after it have not started yet
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
