import type { CSSProperties } from 'react'

/** Where the pointer is over the map, in px from its top left, and the map's size. */
export type MapPointer = { x: number; y: number; width: number; height: number }

/** A tooltip's distance from the pointer and from the map's edges, in px. */
const GAP = 16

/** A map tooltip's place. */
export function placeTooltip(
  { x, y, height, width: mapWidth }: MapPointer,
  width: number,
  tallest: number,
  right: number = mapWidth,
  start = 0,
): CSSProperties {
  const onRight = x + GAP + width <= right - GAP
  const left = onRight ? x + GAP : x - GAP - width
  return {
    left: Math.max(start + GAP, Math.min(left, right - GAP - width)),
    top: Math.max(GAP, Math.min(y - GAP, height - tallest - GAP)),
    width,
  }
}
