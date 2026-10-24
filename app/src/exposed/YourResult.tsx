import type { Ref } from 'react'
import Badge from '../components/Badge.tsx'
import Button from '../components/Button.tsx'
import Icon from '../components/Icon.tsx'
import GuideStep from './GuideStep.tsx'
import { EMERGENCY, HELPLINE_PHONE, LEVEL_BADGES, resultFor, SYMPTOMS_BADGE, type Answers } from './risk.ts'
import './YourResult.css'

type YourResultProps = {
  /** The reader's answers, all five given. */
  answers: Answers
  /** "Find the nearest health center": asks for the phone's location and opens step 3. */
  onFindCenters: () => void
  onBack: () => void
  titleRef: Ref<HTMLHeadingElement>
}

/** Step 2 of the guide: the risk group and what it means. */
export default function YourResult({ answers, onFindCenters, onBack, titleRef }: YourResultProps) {
  const result = resultFor(answers)
  const badge = LEVEL_BADGES[result.level]
  const footer = (
    <>
      <Button icon="arrow-right" onClick={onFindCenters} className="guide-step-button">
        Find the nearest health center
      </Button>
      <Button variant="secondary" href={HELPLINE_PHONE} className="guide-step-button">
        Call QC Helpline 122
      </Button>
    </>
  )

  return (
    <GuideStep step={2} title="Your result" onBack={onBack} titleRef={titleRef} footer={footer}>
      <div className="your-result">
        <section className="your-result-card">
          <div className="your-result-badges">
            {result.symptoms && <Badge tone="alert">{SYMPTOMS_BADGE}</Badge>}
            <Badge tone={badge.tone}>{badge.label}</Badge>
          </div>
          <h2 className="heading-m">{result.heading}</h2>
          <p className="your-result-summary body-m">{result.summary}</p>
        </section>
        <section className="your-result-todo">
          <h2 className="heading-s">What to do</h2>
          <ol className="your-result-steps">
            {result.steps.map((step, i) => (
              <li key={step} className="your-result-step body-m">
                <span className="your-result-number label-ui-s" aria-hidden="true">
                  {i + 1}
                </span>
                {step}
              </li>
            ))}
          </ol>
        </section>
        <aside className="your-result-urgent" aria-label="Emergency">
          <Icon name="info" size={20} className="your-result-urgent-icon" />
          <p className="body-s">
            {EMERGENCY.signs}
            <a href={HELPLINE_PHONE} className="your-result-call">
              {EMERGENCY.call}
            </a>
            .
          </p>
        </aside>
      </div>
    </GuideStep>
  )
}
