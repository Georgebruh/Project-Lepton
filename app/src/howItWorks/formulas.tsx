import type { ReactNode } from 'react'
import type { FormulaId } from './content.ts'

/** A model's formula: the equations, then each symbol in plain words. */
type Formula = { lines: ReactNode[]; terms: [ReactNode, string][]; plainly?: string }

/**
 * F10: the formulas behind "Show the formula" in the models table, as lepton-plan.md writes
 * them (B5 for M4, B8 for M0 and M1, B7 for the threshold). The plan keeps formulas out of the
 * page's main text, so each sits behind its button. Written in HTML (sub, sup) rather than a
 * math library, which the app does not load.
 */
export const FORMULAS: Record<FormulaId, Formula> = {
  m0: {
    lines: [
      <>
        ŷ<sub>T+1</sub> = y<sub>T+1−52</sub>
      </>,
    ],
    terms: [
      [<>ŷ<sub>T+1</sub></>, 'the forecast for the target week, one week after the forecast day T'],
      [<>y<sub>T+1−52</sub></>, 'the count in the same week one year (52 weeks) earlier'],
    ],
  },
  m1: {
    lines: [
      <>
        ŷ<sub>w</sub> = ȳ<sub>w</sub>
      </>,
      <>
        T<sub>w</sub> = ȳ<sub>w</sub> + 2 s<sub>w</sub>, &nbsp; Pr(breach) = Pr(Y &gt; T<sub>w</sub>)
      </>,
    ],
    terms: [
      [
        <>ȳ<sub>w</sub>, s<sub>w</sub></>,
        'the mean and standard deviation of week w over up to the 5 most recent complete years before the target year, at least 3, leaving out 2020–2021; week 53 uses week 52',
      ],
      [<>T<sub>w</sub></>, 'the epidemic threshold for week w, which every model’s breach chance uses'],
      [<>Y</>, 'the week’s final count; a breach is a count strictly greater than the threshold'],
    ],
  },
  m4: {
    lines: [
      <>
        log μ<sub>T+1</sub> = log P<sub>T</sub> + β<sub>0</sub> + Σ<sub>k=1…3</sub> [α<sub>k</sub>{' '}
        sin(2πkt / 52.18) + γ<sub>k</sub> cos(2πkt / 52.18)]
      </>,
      <>
        &emsp;+ ρ log(1 + ỹ) + β<sub>1</sub> Rcum2<sub>T</sub> / 50 + β<sub>2</sub> EI2<sub>T</sub> + δ
        COVID<sub>T+1</sub>
      </>,
    ],
    terms: [
      [<>μ<sub>T+1</sub></>, 'the expected cases in the target week'],
      [<>P<sub>T</sub></>, 'Quezon City’s population, the offset'],
      [<>α<sub>k</sub>, γ<sub>k</sub></>, 'three sine and cosine pairs for the season; t counts the weeks up to the target week, 52.18 to a year'],
      [<>ỹ</>, 'the cases of the last two weeks the model may see'],
      [<>Rcum2<sub>T</sub></>, 'the last two weeks’ rain in mm, weighted to where people live'],
      [<>EI2<sub>T</sub></>, 'the flood exposure index, the larger of the last two weeks'],
      [<>COVID<sub>T+1</sub></>, '1 for target weeks in 2020–2021, otherwise 0'],
    ],
    plainly:
      'In plain words: expected cases = population × base rate × season × a recent-cases multiplier × a rain multiplier × a flood multiplier × a COVID multiplier. Cases follow a negative binomial with that mean; its 5% and 95% points give the 90% range.',
  },
}
