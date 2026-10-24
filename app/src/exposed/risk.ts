/** The questions of the "I have been exposed to floodwater" guide, and what each set of answers means. */

/** The five questions' keys, in the order the guide asks them. */
export type QuestionKey = 'when' | 'times' | 'wound' | 'splash' | 'symptoms'

export type Option = { value: string; label: string }

export type Question = { key: QuestionKey; text: string; options: Option[] }

/** The five questions and their answers. */
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

/** The reader's risk group. */
export function riskLevel(answers: Answers): RiskLevel {
  if (answers.times === 'more') {
    return 'high'
  }
  if (answers.wound === 'yes' || answers.splash === 'yes' || answers.splash === 'not sure') {
    return 'moderate'
  }
  return 'low'
}

/** Each group's badge. */
export const LEVEL_BADGES: Record<RiskLevel, { label: string; tone: 'neutral' | 'warn' | 'alert' }> = {
  low: { label: 'Low risk', tone: 'neutral' },
  moderate: { label: 'Moderate risk', tone: 'warn' },
  high: { label: 'High risk', tone: 'alert' },
}

/** The badge beside the risk group when the reader has fever, muscle pain or red eyes now. */
export const SYMPTOMS_BADGE = 'Symptoms now'

/** The emergency box on every result. */
export const EMERGENCY = 'Yellow eyes, dark urine, bleeding or trouble breathing? Go to a hospital now.'

/** What the guide tells the reader. */
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

/** What to do, by group. */
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

/** The step that says what to tell the health worker. */
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
