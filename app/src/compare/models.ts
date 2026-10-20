/**
 * F9: B10's five models as Compare models shows them: each one's name, chart color and line.
 * Names and colors are Figma's model toggles (frame "Compare models", node 12:982), where M4,
 * LEPTON's model, is always teal and the published benchmark M3 is blue. The baselines and the
 * flood test are grey, so the two that matter stand out (the notes beside the frame).
 *
 * The three greys are hard to tell apart when more than one is on (dataviz validator: M0 and
 * "M4 without flood index" are only 9.8 apart, under the floor of 15), so two of them get a
 * dash pattern as well; the tooltip and the table view name every line.
 */

export type ModelStyle = {
  /** The name on its toggle and in the score table, as Figma writes it. */
  name: string
  /** The shorter name in the chart's key and its tooltip. */
  key: string
  /** Its line's color: a token, never a hex. */
  color: string
  /** Its line's width in px (Figma: M4 2.25, M3 1.75). */
  width: number
  /** SVG stroke-dasharray for the greys that need one; undefined for a solid line. */
  dash?: string
  /** Whether its toggle starts on (Figma: M4 and M3). */
  on: boolean
}

/** Keyed by the model's name in city_forecast.json and scores.json (B10, with D6's M4_no_EI2). */
const STYLES: Record<string, ModelStyle> = {
  M4: { name: 'M4 · LEPTON (ours)', key: 'M4', color: 'var(--color-chart-m4)', width: 2.25, on: true },
  M3: { name: 'M3 · Prophet + XGBoost', key: 'M3', color: 'var(--color-chart-m3)', width: 1.75, on: true },
  M1: { name: 'M1 · Seasonal average', key: 'M1', color: 'var(--color-chart-m1)', width: 1.5, on: false },
  M0: { name: 'M0 · Same week last year', key: 'M0', color: 'var(--color-chart-m0)', width: 1.5, dash: '1 3', on: false },
  M4_no_EI2: {
    name: 'M4 without flood index',
    key: 'M4 without flood index',
    color: 'var(--color-text-tertiary)',
    width: 1.5,
    dash: '7 4',
    on: false,
  },
}

/** The model whose 90% range the chart shades (the plan: "M4's 90% range"). */
export const RANGE_MODEL = 'M4'

/** The toggles' order, as in Figma: ours, the benchmark, the two baselines, then the flood test. */
const TOGGLE_ORDER = ['M4', 'M3', 'M1', 'M0', 'M4_no_EI2']

/** A model's style; a model this file does not know is grey and off, under its own name. */
export function modelStyle(model: string): ModelStyle {
  return STYLES[model] ?? { name: model, key: model, color: 'var(--color-text-tertiary)', width: 1.5, on: false }
}

/** The models of city_forecast.json in the toggles' order; any model not listed there goes last. */
export function toggleOrder(models: string[]): string[] {
  const rank = (model: string) => (TOGGLE_ORDER.includes(model) ? TOGGLE_ORDER.indexOf(model) : TOGGLE_ORDER.length)
  return [...models].sort((a, b) => rank(a) - rank(b))
}
