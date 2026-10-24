/** The five models as Compare models shows them: each one's name, chart color and line. */

export type ModelStyle = {
  /** The name on its toggle and in the score table, as written. */
  name: string
  /** The shorter name in the chart's key and its tooltip. */
  key: string
  /** Its line's color: a token, never a hex. */
  color: string
  /** Its line's width in px. */
  width: number
  /** SVG stroke-dasharray for the greys that need one; undefined for a solid line. */
  dash?: string
  /** Whether its toggle starts on. */
  on: boolean
}

/** Keyed by the model's name in city_forecast.json and scores.json. */
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

/** The model whose 90% range the chart shades. */
export const RANGE_MODEL = 'M4'

/** The toggles' order: ours, the benchmark, the two baselines, then the flood test. */
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
