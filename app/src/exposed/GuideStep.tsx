import type { ReactNode, Ref } from 'react'
import Icon from '../components/Icon.tsx'
import './GuideStep.css'

/** The guide's steps: the questions, the result, the nearest health centers. */
const STEPS = [1, 2, 3]

type GuideStepProps = {
  /** Which step this is, 1 to 3. */
  step: number
  /** The step's name in the top bar, e.g. "Exposure check". */
  title: string
  /** What Back in the top bar does. */
  onBack: () => void
  /** The title, which the guide focuses when a new step opens, so a screen reader starts there. */
  titleRef: Ref<HTMLHeadingElement>
  /** The buttons (and notes) at the bottom. */
  footer: ReactNode
  /** The step's own content. */
  children: ReactNode
}

/** One step of the "I have been exposed to floodwater" guide. */
export default function GuideStep({ step, title, onBack, titleRef, footer, children }: GuideStepProps) {
  return (
    <main className="guide-step">
      <header className="guide-step-top">
        <div className="guide-step-bar">
          <button type="button" className="guide-step-back" onClick={onBack} aria-label="Back">
            <Icon name="chevron-left" size={22} />
          </button>
          <h1 ref={titleRef} tabIndex={-1} className="guide-step-title heading-s">
            {title}
          </h1>
          <p className="guide-step-count label-ui-s">
            <span className="visually-hidden">Step </span>
            {step} of {STEPS.length}
          </p>
        </div>
        <div className="guide-step-progress" aria-hidden="true">
          {STEPS.map((part) => (
            <span key={part} className={part <= step ? 'guide-step-part guide-step-part-done' : 'guide-step-part'} />
          ))}
        </div>
      </header>
      <div className="guide-step-body">{children}</div>
      <footer className="guide-step-footer">{footer}</footer>
    </main>
  )
}
