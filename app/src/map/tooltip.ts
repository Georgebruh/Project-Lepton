import type { CSSProperties } from 'react'

/** F4 and F5: where the pointer is over the map, in px from its top left, and the map's size. */
export type MapPointer = { x: number; y: number; width: number; height: number }

/** A tooltip's distance from the pointer and from the map's edges, in px (Figma). */
const GAP = 16

/**
 * A map tooltip's place: right of the pointer, or left of it when it would pass `right` (the
 * right edge of the map the reader sees), and kept inside the map. `tallest` is the most the
 * tooltip is ever tall, so that it never runs off the bottom. F11: on a phone neither side may
 * have room, so the tooltip is also kept off the left edge. F14: `start` is the left edge of the
 * map the reader sees (the city panel covers the map's left side).
 */
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
