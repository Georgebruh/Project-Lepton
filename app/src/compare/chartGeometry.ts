/** The chart's geometry, in plain functions. */

/** Room around the plot, px: the counts' labels on the left, the dates below. */
export const MARGIN = { top: 8, right: 8, bottom: 28, left: 36 }

/** Extra room on top for the storms' names, so they never sit on the data. */
export const STORM_LABEL_ROOM = 16

/** The plot: 330 px tall at 1030 px wide; narrower charts keep that shape, but no lower than 220 px. */
const FIGMA_WIDTH = 1030
const FIGMA_HEIGHT = 330
const MIN_HEIGHT = 220

/** How far the counts axis may reach above the tallest count or forecast: half again. */
export const REFERENCE_HEADROOM = 1.5

/** Bars are 10.4 px in a 19.3 px week (54%), at most 24 px; under 4 px a week, they touch. */
const BAR_SHARE = 0.54
const BAR_MAX = 24
const BAR_TOUCH = 4

/** An axis label's width. */
const LABEL_CHAR = 7
const LABEL_GAP = 8

/** The room between a storm's line and its name, px. */
const NAME_PAD = 4

/** The plot's height for the chart's width. */
export function plotHeight(width: number): number {
  return Math.max(MIN_HEIGHT, Math.min(FIGMA_HEIGHT, Math.round((width * FIGMA_HEIGHT) / FIGMA_WIDTH)))
}

/** The top of the counts axis, before rounding to a round number. */
export function axisTop(dataMax: number, referenceMax: number): number {
  if (dataMax <= 0) {
    return Math.max(1, referenceMax)
  }
  return Math.max(dataMax, Math.min(referenceMax, REFERENCE_HEADROOM * dataMax))
}

/** A bar's width for weeks `step` px apart. */
export function barWidth(step: number): number {
  return step < BAR_TOUCH ? step : Math.min(BAR_MAX, BAR_SHARE * step)
}

/** The width an axis label takes, px. */
export function labelWidth(label: string): number {
  return label.length * LABEL_CHAR
}

/** The left margin: room for the longest counts label ("1,200") and a gap, at least 36 px. */
export function leftMargin(labels: string[]): number {
  return Math.max(MARGIN.left, Math.max(0, ...labels.map(labelWidth)) + LABEL_GAP)
}

/** An SVG line through the points, left to right: "M x y L x y ...", to 0.1 px. */
export function linePath(points: [number, number][]): string {
  return points.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join('')
}

/** A closed SVG area between `top` (left to right) and `bottom` (the same xs), for a range. */
export function areaPath(top: [number, number][], bottom: [number, number][]): string {
  const back = [...bottom].reverse().map(([x, y]) => `L${x.toFixed(1)} ${y.toFixed(1)}`)
  return `${linePath(top)}${back.join('')}Z`
}

/** The labels that fit, left to right: a label is dropped when it would touch the one kept before it. */
export function fittingLabels<T extends { x: number; label: string }>(labels: T[], anchor: 'start' | 'middle'): T[] {
  const kept: T[] = []
  let end = -Infinity
  for (const item of labels) {
    const width = labelWidth(item.label)
    const left = anchor === 'start' ? item.x : item.x - width / 2
    if (left >= end + LABEL_GAP) {
      kept.push(item)
      end = left + width
    }
  }
  return kept
}

/** A name placed beside its line: where its text starts or ends (`textX`), and which. */
export type PlacedName<T> = T & { textX: number; anchor: 'start' | 'end' }

/** The storms' names above the plot, left to right. */
export function placeNames<T extends { x: number; label: string }>(items: T[], right: number): PlacedName<T>[] {
  const placed: PlacedName<T>[] = []
  let end = -Infinity
  for (const item of items) {
    const width = labelWidth(item.label)
    const anchor = item.x + NAME_PAD + width <= right ? 'start' : 'end'
    const left = anchor === 'start' ? item.x + NAME_PAD : item.x - NAME_PAD - width
    if (left >= end + LABEL_GAP) {
      placed.push({ ...item, textX: anchor === 'start' ? item.x + NAME_PAD : item.x - NAME_PAD, anchor })
      end = left + width
    }
  }
  return placed
}
