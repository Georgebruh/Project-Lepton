/**
 * F8: the questions of the "I have been exposed to floodwater" guide, and what each set of
 * answers means. Plain functions, no React.
 *
 * The rule is the guide's notes in Figma ("Notes · Exposure guide", node 40:356), which put
 * DOH DM 2023-0309's three risk groups in a resident's words:
 *   - in floodwater more than once, or for 2 days or more: high risk;
 *   - otherwise, a cut or wound, or floodwater in the eyes, nose or mouth: moderate risk;
 *   - otherwise: low risk.
 * Fever, muscle pain or red eyes now come first: the result says "see a doctor today".
 *
 * The guide never names a medicine or a dose: a doctor or nurse decides (DM 2023-0309 requires
 * a physician's consultation before any prophylaxis). Where the advice comes from (doh.gov.ph
 * blocks automated reading; the wording was checked through search results on 2026-10-20):
 *   - DOH press release, "DOH on Code White; leptospirosis has prophylaxis": see a doctor or a
 *     health center within 24-48 hours after first wading in floodwater.
 *     https://doh.gov.ph/press-release/doh-on-code-white-leptospirosis-has-prophylaxis/
 *   - DOH press release, "Rain raises lepto cases, DOH calls for prompt medical consult after
 *     floods" (July 2024): within 24 hours.
 *     https://doh.gov.ph/press-release/rain-raises-lepto-cases-doh-calls-for-prompt-medical-consult-after-floods/
 *   - DOH health advisory, Leptospirosis: fever, muscle pain and red eyes appear 2 to 30 days
 *     after exposure; yellow skin or eyes and dark urine in severe cases; boots and gloves when
 *     wading cannot be avoided. https://doh.gov.ph/Health-Advisory/Leptospirosis
 *   - QC Helpline 122, the city's 24/7 line: https://quezoncity.gov.ph/program/qc-helpline-122/
 * Figma words only the moderate result; the low and high results and the symptoms result
 * follow its pattern. A health professional should review this wording before launch, as F7's
 * page asks for its own.
 */

/** The five questions' keys, in the order the guide asks them. */
export type QuestionKey = 'when' | 'times' | 'wound' | 'splash' | 'symptoms'

export type Option = { value: string; label: string }

export type Question = { key: QuestionKey; text: string; options: Option[] }

/** The five questions and their answers, as Figma frame "1 Exposure check" (39:301) words them. */
export const QUESTIONS: Question[] = [
  {
    key: 'when',
    text: 'When were you in floodwater?',
    options: [
      { value: 'today', label: 'Today' },
      { value: '1-2 days', label: '1–2 days ago' },
      { value: '3-7 days', label: '3–7 days ago' },
      { value: 'over a week', label: 'Over a week ago' },
    ],
  },
  {
    key: 'times',
    text: 'How many times, or how long?',
    options: [
      { value: 'once', label: 'Once' },
      { value: 'more', label: 'More than once, or 2+ days' },
    ],
  },
  {
    key: 'wound',
    text: 'Did you have a cut or wound on your skin?',
    options: [
      { value: 'yes', label: 'Yes' },
      { value: 'no', label: 'No' },
    ],
  },
  {
    key: 'splash',
    text: 'Did floodwater get in your eyes, nose or mouth?',
    options: [
      { value: 'yes', label: 'Yes' },
      { value: 'no', label: 'No' },
      { value: 'not sure', label: 'Not sure' },
    ],
  },
  {
    key: 'symptoms',
    text: 'Do you have fever, muscle pain or red eyes now?',
    options: [
      { value: 'yes', label: 'Yes' },
      { value: 'no', label: 'No' },
    ],
  },
]

/** The reader's answers: each question's chosen option (its `value`), or null while unanswered. */
export type Answers = Record<QuestionKey, string | null>

/** Nothing answered yet. The answers live only in the page's memory: never stored or sent. */
export const NO_ANSWERS: Answers = { when: null, times: null, wound: null, splash: null, symptoms: null }

/** The questions still unanswered, in the guide's order. */
export function unanswered(answers: Answers): QuestionKey[] {
  return QUESTIONS.filter(({ key }) => answers[key] === null).map(({ key }) => key)
}

export type RiskLevel = 'low' | 'moderate' | 'high'

/**
 * The reader's risk group, by the guide's notes: in floodwater more than once or for 2 days or
 * more is high; otherwise a cut or wound, or floodwater in the eyes, nose or mouth, is moderate;
 * otherwise low. "Not sure" about the eyes, nose or mouth counts as yes (assumption: missing a
 * splash costs more than one more visit to a health center, and a nurse checks either way).
 */
export function riskLevel(answers: Answers): RiskLevel {
  if (answers.times === 'more') {
    return 'high'
  }
  if (answers.wound === 'yes' || answers.splash === 'yes' || answers.splash === 'not sure') {
    return 'moderate'
  }
  return 'low'
}

/** Each group's badge (the Badge component's tone: amber for moderate, as in Figma; red for high). */
export const LEVEL_BADGES: Record<RiskLevel, { label: string; tone: 'neutral' | 'warn' | 'alert' }> = {
  low: { label: 'Low risk', tone: 'neutral' },
  moderate: { label: 'Moderate risk', tone: 'warn' },
  high: { label: 'High risk', tone: 'alert' },
}

/** The badge beside the risk group when the reader has fever, muscle pain or red eyes now. */
export const SYMPTOMS_BADGE = 'Symptoms now'

/**
 * The emergency box on every result (the guide's notes): signs of severe leptospirosis, which
 * cannot wait for a health center. `call` is the part of the sentence that dials QC Helpline 122.
 */
export const EMERGENCY = {
  signs: 'Yellow eyes, dark urine, bleeding or trouble breathing? Go to a hospital now, or ',
  call: 'call QC Helpline 122',
}

/** QC Helpline 122's number, for the links that dial it. */
export const HELPLINE_PHONE = 'tel:122'

/** What the guide tells the reader: Figma frame "2 Your result" (39:361). */
export type Result = {
  level: RiskLevel
  /** Fever, muscle pain or red eyes now: "see a doctor today" comes first. */
  symptoms: boolean
  heading: string
  /** What the answers say, then who decides on medicine. */
  summary: string
  /** What to do, in order. */
  steps: string[]
}

/** The heading of each group without symptoms. DOH: see a health worker within 24-48 hours of wading. */
const HEADINGS: Record<RiskLevel, string> = {
  low: 'Go to a health center within 24–48 hours',
  moderate: 'Go to a health center within 24–48 hours',
  high: 'Go to a health center today',
}

/** The result for a full set of answers (every question answered). */
export function resultFor(answers: Answers): Result {
  const level = riskLevel(answers)
  const symptoms = answers.symptoms === 'yes'
  const decides = symptoms
    ? 'Fever, muscle pain or red eyes after being in floodwater can be early signs of leptospirosis. A doctor will check you and decide on your treatment.'
    : 'A doctor or nurse will check you and decide if you need preventive medicine.'
  return {
    level,
    symptoms,
    heading: symptoms ? 'See a doctor today' : HEADINGS[level],
    summary: `${exposureSentence(answers)} ${decides}`,
    steps: stepsFor(answers, level, symptoms),
  }
}

const NO_ANTIBIOTICS = 'Don’t take antibiotics on your own.'

/**
 * What to do, by group: Figma's four steps for moderate risk (and low); high risk goes today and
 * adds boots and gloves, since its exposure may go on; with symptoms, a doctor today replaces
 * the watch for symptoms.
 */
function stepsFor(answers: Answers, level: RiskLevel, symptoms: boolean): string[] {
  const tell = tellStep(answers)
  if (symptoms) {
    return ['See a doctor today, at a health center or a hospital.', tell, NO_ANTIBIOTICS]
  }
  // Symptoms show 2 to 30 days after exposure (DOH): count the 4 weeks from the wading
  const watch =
    answers.when === 'over a week'
      ? 'Watch for fever or muscle pain until 4 weeks after you waded.'
      : 'Watch for fever or muscle pain over the next 4 weeks.'
  if (level === 'high') {
    return [
      'Visit a health center today.',
      tell,
      NO_ANTIBIOTICS,
      'If you must wade again, wear rubber boots and gloves.',
      watch,
    ]
  }
  return ['Visit a health center today or tomorrow.', tell, NO_ANTIBIOTICS, watch]
}

/** What the answers say, in one sentence: "You waded once with a cut on your skin." */
export function exposureSentence(answers: Answers): string {
  const more = answers.times === 'more'
  const start = more ? 'You were in floodwater more than once, or for 2 days or more' : 'You waded once'
  const cut = answers.wound === 'yes' ? `${more ? ',' : ''} with a cut on your skin` : ''
  if (answers.splash === 'yes') {
    return `${start}${cut}, and floodwater got in your eyes, nose or mouth.`
  }
  if (answers.splash === 'not sure') {
    return `${start}${cut}, and you’re not sure if floodwater got in your eyes, nose or mouth.`
  }
  if (cut || more) {
    return `${start}${cut}.`
  }
  return `${start}, with no cut on your skin and no floodwater in your eyes, nose or mouth.`
}

/** The step that says what to tell the health worker: "Tell them when and where you waded, and about your cut." */
function tellStep(answers: Answers): string {
  const start =
    answers.times === 'more'
      ? 'Tell them when, where and how long you were in floodwater'
      : 'Tell them when and where you waded'
  const details: string[] = []
  if (answers.wound === 'yes') {
    details.push('about your cut')
  }
  if (answers.splash === 'yes') {
    details.push('that floodwater got in your eyes, nose or mouth')
  }
  if (answers.splash === 'not sure') {
    details.push('that floodwater may have gotten in your eyes, nose or mouth')
  }
  if (answers.symptoms === 'yes') {
    details.push('about your symptoms')
  }
  if (details.length === 0) {
    return `${start}.`
  }
  // "…, and about your cut." or "…, about your cut, and that floodwater got in …"
  const last = details.pop()
  return `${start}, ${[...details, `and ${last}`].join(', ')}.`
}
