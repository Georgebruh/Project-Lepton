import type { ReactNode } from 'react'
import './Facts.css'

/** One fact: what it is, and its value ("90% range", "1–39 cases"). */
export type Fact = { label: string; value: ReactNode }

type FactsProps = {
  facts: Fact[]
  className?: string
}

/** The city panel's facts, one row each: the label on the left, the value on the right (Figma "Key value row"). */
export default function Facts({ facts, className }: FactsProps) {
  return (
    <dl className={className ? `facts ${className}` : 'facts'}>
      {facts.map(({ label, value }) => (
        <div key={label} className="facts-row">
          <dt className="facts-label body-s">{label}</dt>
          <dd className="facts-value label-ui">{value}</dd>
        </div>
      ))}
    </dl>
  )
}
