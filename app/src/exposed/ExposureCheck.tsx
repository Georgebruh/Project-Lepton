import { useId, useState, type Ref } from 'react'
import Button from '../components/Button.tsx'
import GuideStep from './GuideStep.tsx'
import { QUESTIONS, unanswered, type Answers, type QuestionKey } from './risk.ts'
import './ExposureCheck.css'

type ExposureCheckProps = {
  answers: Answers
  /** Called with each answer the reader chooses. */
  onAnswer: (key: QuestionKey, value: string) => void
  /** Called by "See what to do" once every question has an answer. */
  onDone: () => void
  onBack: () => void
  titleRef: Ref<HTMLHeadingElement>
}

/**
 * F8: step 1 of the guide, Figma frame "1 Exposure check" (39:301): five questions, each a row
 * of answers to choose one from. Each row is a group of radio buttons drawn as Figma's answer
 * chips, so the arrow keys move between answers and a screen reader reads "1 of 4". "See what to
 * do" opens the result once all five are answered; until then it marks the questions left and
 * moves to the first.
 */
export default function ExposureCheck({ answers, onAnswer, onDone, onBack, titleRef }: ExposureCheckProps) {
  const id = useId()
  // Whether the reader tried to go on with questions unanswered: only then are they marked
  const [tried, setTried] = useState(false)
  const missing = unanswered(answers)

  function seeWhatToDo() {
    if (missing.length > 0) {
      setTried(true)
      // Bring the first question left into the middle of the screen, clear of the footer, and
      // move the keyboard to its first answer
      document.getElementById(`${id}-${missing[0]}-group`)?.scrollIntoView({ block: 'center' })
      document.getElementById(`${id}-${missing[0]}-0`)?.focus({ preventScroll: true })
      return
    }
    onDone()
  }

  const footer = (
    <>
      {tried && missing.length > 0 && (
        <p className="exposure-check-left body-s" role="status">
          {missing.length === 1
            ? 'Answer the question marked above to see what to do.'
            : `Answer the ${missing.length} questions marked above to see what to do.`}
        </p>
      )}
      <Button icon="arrow-right" onClick={seeWhatToDo} className="guide-step-button">
        See what to do
      </Button>
    </>
  )

  return (
    <GuideStep step={1} title="Exposure check" onBack={onBack} titleRef={titleRef} footer={footer}>
      <div className="exposure-check">
        <h2 className="heading-m">Tell us about your exposure</h2>
        <p className="exposure-check-intro body-m">Five quick questions. We don’t ask for your name.</p>
        {QUESTIONS.map(({ key, text, options }) => {
          const marked = tried && answers[key] === null
          return (
            <div
              key={key}
              id={`${id}-${key}-group`}
              className="exposure-check-question"
              role="radiogroup"
              aria-labelledby={`${id}-${key}`}
              aria-describedby={marked ? `${id}-${key}-left` : undefined}
              aria-required="true"
            >
              <p id={`${id}-${key}`} className="exposure-check-text label-ui">
                {text}
              </p>
              {marked && (
                <p id={`${id}-${key}-left`} className="exposure-check-left body-s">
                  Choose an answer.
                </p>
              )}
              <div className="exposure-check-options">
                {options.map((option, i) => {
                  const chosen = answers[key] === option.value
                  return (
                    <label
                      key={option.value}
                      className={
                        chosen ? 'exposure-check-option exposure-check-chosen label-ui' : 'exposure-check-option label-ui'
                      }
                    >
                      <input
                        id={`${id}-${key}-${i}`}
                        className="exposure-check-input"
                        type="radio"
                        name={`${id}-${key}`}
                        value={option.value}
                        checked={chosen}
                        onChange={() => onAnswer(key, option.value)}
                      />
                      {option.label}
                    </label>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </GuideStep>
  )
}
