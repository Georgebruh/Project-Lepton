import { useEffect, useState } from 'react'
import Badge from '../components/Badge.tsx'
import Button from '../components/Button.tsx'
import Footer from '../components/Footer.tsx'
import SiteHeader from '../components/SiteHeader.tsx'
import Tab from '../components/Tab.tsx'
import {
  DATA_SOURCES,
  FUTURE_WORK,
  LIMITS,
  MODELS,
  PAPERS,
  PHOTO_SOURCES,
  PIPELINE,
  TESTS,
  type FormulaId,
  type PipelineCard,
  type Reference,
} from '../howItWorks/content.ts'
import { FORMULAS } from '../howItWorks/formulas.tsx'
import './HowItWorks.css'

/** The five sections, in order: the tabs' labels and the ids they jump to. */
const SECTIONS = [
  { id: 'pipeline', label: 'Pipeline' },
  { id: 'models', label: 'Models' },
  { id: 'testing', label: 'Testing' },
  { id: 'limits', label: 'Limits' },
  { id: 'sources', label: 'Sources' },
]

/**
 * The section being read: the last one whose top has passed a third of the way down the
 * window, or the last section once the page is scrolled to the bottom.
 */
function useCurrentSection() {
  const [current, setCurrent] = useState(SECTIONS[0].id)
  useEffect(() => {
    const update = () => {
      const atBottom = window.innerHeight + window.scrollY >= document.body.scrollHeight - 2
      let found = SECTIONS[0].id
      for (const { id } of SECTIONS) {
        const top = document.getElementById(id)?.getBoundingClientRect().top
        if (top !== undefined && top <= window.innerHeight / 3) found = id
      }
      setCurrent(atBottom ? SECTIONS[SECTIONS.length - 1].id : found)
    }
    update()
    window.addEventListener('scroll', update, { passive: true })
    window.addEventListener('resize', update)
    return () => {
      window.removeEventListener('scroll', update)
      window.removeEventListener('resize', update)
    }
  }, [])
  return current
}

/** A section's numbered eyebrow ("01 · Pipeline") over its heading. */
function SectionHead({ id, number, title }: { id: string; number: string; title: string }) {
  return (
    <div className="how-it-works-section-head">
      <p className="how-it-works-eyebrow label-eyebrow">{number}</p>
      <h2 id={`${id}-title`} className="heading-l">
        {title}
      </h2>
    </div>
  )
}

function Intro({ current }: { current: string }) {
  return (
    <section className="how-it-works-intro" aria-labelledby="how-it-works-title">
      <p className="how-it-works-eyebrow-accent label-eyebrow">Method</p>
      <h1 id="how-it-works-title" className="display-l">
        How LEPTON works
      </h1>
      <p className="how-it-works-intro-lead body-l">
        One shared flood computation feeds two models: a city forecast for next week’s cases, and a
        barangay stock plan for the next one to three days. Every number on this site comes from
        the code in our repository.
      </p>
      <nav className="how-it-works-tabs" aria-label="Sections">
        {SECTIONS.map(({ id, label }) => (
          <Tab key={id} href={`#${id}`} selected={current === id}>
            {label}
          </Tab>
        ))}
      </nav>
    </section>
  )
}

/** The five ramp steps under the exposure index card, from nobody (R0) to the 100-year map. */
function ExposureRamp() {
  return (
    <div className="how-it-works-ramp" aria-hidden="true">
      <div className="how-it-works-ramp-steps">
        {[1, 2, 3, 4, 5].map((step) => (
          <span key={step} style={{ background: `var(--color-data-ramp-${step})` }} />
        ))}
      </div>
      <div className="how-it-works-ramp-labels label-eyebrow">
        <span>
          R<sub>0</sub> · nobody
        </span>
        <span>R(100)</span>
      </div>
    </div>
  )
}

/** One card of the diagram; the shared computation's card is tinted and carries the ramp. */
function DiagramCard({ card, shared }: { card: PipelineCard; shared: boolean }) {
  return (
    <li className={shared ? 'how-it-works-card is-shared' : 'how-it-works-card'}>
      <p className="how-it-works-card-label label-eyebrow">{card.label}</p>
      <h3 className="heading-s">{card.title}</h3>
      <p className="how-it-works-card-text body-s">{card.text}</p>
      {card.awaited && <Badge tone="warn">Simulated until QCESD data</Badge>}
      {shared && <ExposureRamp />}
    </li>
  )
}

function Pipeline() {
  return (
    <section id="pipeline" className="how-it-works-section" aria-labelledby="pipeline-title">
      <SectionHead id="pipeline" number="01 · Pipeline" title="From rain to a stock list in four steps" />
      <div className="how-it-works-pipeline-links">
        <p className="body-m">
          The numbers it makes are on the map, with the city’s forecast and each storm’s stock
          plan, and in Compare models, with every model’s weekly forecast and score.
        </p>
        <div className="how-it-works-pipeline-buttons">
          <Button variant="secondary" icon="arrow-right" to="/map">
            Open the map
          </Button>
          <Button variant="secondary" icon="arrow-right" to="/map/quezon-city/compare?data=real">
            Compare models
          </Button>
        </div>
      </div>
      <ol className="how-it-works-diagram">
        {PIPELINE.map(({ step, cards }, i) => (
          <li key={step} className="how-it-works-step">
            <p className="how-it-works-eyebrow label-eyebrow">{step}</p>
            <ul className="how-it-works-step-cards">
              {cards.map((card) => (
                <DiagramCard key={card.title} card={card} shared={i === 1} />
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </section>
  )
}

/** "Show the formula": a model's formula and its symbols in plain words, closed at first. */
function ShowFormula({ id }: { id: FormulaId }) {
  const { lines, terms, plainly } = FORMULAS[id]
  return (
    <details className="how-it-works-formula">
      <summary className="label-ui">
        <span className="how-it-works-formula-show">Show the formula</span>
        <span className="how-it-works-formula-hide">Hide the formula</span>
      </summary>
      <div className="how-it-works-formula-body">
        <div className="how-it-works-formula-math body-m">
          {lines.map((line, i) => (
            <p key={i}>{line}</p>
          ))}
        </div>
        <dl className="how-it-works-formula-terms body-s">
          {terms.map(([symbol, meaning], i) => (
            <div key={i}>
              <dt>{symbol}</dt>
              <dd>{meaning}</dd>
            </div>
          ))}
        </dl>
        {plainly && <p className="how-it-works-formula-plainly body-s">{plainly}</p>}
      </div>
    </details>
  )
}

function Models() {
  return (
    <section id="models" className="how-it-works-section" aria-labelledby="models-title">
      <SectionHead id="models" number="02 · Models" title="Our model against a published one and two baselines" />
      <div className="how-it-works-table-wrap">
        <table className="how-it-works-models">
          <thead>
            <tr className="label-eyebrow">
              <th scope="col">Model</th>
              <th scope="col">What it does</th>
              <th scope="col">Role</th>
            </tr>
          </thead>
          <tbody>
            {MODELS.map(({ name, text, role, formula, ours }) => (
              <tr key={name} className={ours ? 'is-ours' : undefined}>
                <th scope="row" className="heading-s">
                  {name}
                </th>
                <td className="how-it-works-models-text body-m">
                  {text}
                  {formula && <ShowFormula id={formula} />}
                </td>
                <td className="how-it-works-models-role">
                  {role.tone ? (
                    <Badge tone={role.tone}>{role.label}</Badge>
                  ) : (
                    <span className="body-s">{role.label}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Testing() {
  return (
    <section id="testing" className="how-it-works-section" aria-labelledby="testing-title">
      <SectionHead id="testing" number="03 · Testing" title="How we check it, before anyone relies on it" />
      <ul className="how-it-works-tests">
        {TESTS.map(({ label, title, text }) => (
          <li key={title} className="how-it-works-test">
            <p className="how-it-works-eyebrow-accent label-eyebrow">{label}</p>
            <h3 className="heading-m">{title}</h3>
            <p className="how-it-works-test-text body-m">{text}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}

function Limits() {
  return (
    <section id="limits" className="how-it-works-section" aria-labelledby="limits-title">
      <SectionHead id="limits" number="04 · Limits" title="What LEPTON can’t do yet" />
      <ul className="how-it-works-limits">
        {LIMITS.map(({ title, text }) => (
          <li key={title} className="how-it-works-limit">
            <h3 className="heading-s">{title}</h3>
            <p className="how-it-works-limit-text body-m">{text}</p>
          </li>
        ))}
      </ul>
      <p className="how-it-works-future body-m">{FUTURE_WORK}</p>
    </section>
  )
}

/** A list of references, each linking to its paper, data set or page (data shared on request has no link). */
function ReferenceList({ title, references }: { title: string; references: Reference[] }) {
  return (
    <div className="how-it-works-references">
      <h3 className="how-it-works-eyebrow label-eyebrow">{title}</h3>
      <ul>
        {references.map(({ text, url }) => (
          <li key={text} className="body-s">
            {url ? (
              <a href={url} target="_blank" rel="noreferrer">
                {text}
              </a>
            ) : (
              text
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

function Sources() {
  return (
    <section id="sources" className="how-it-works-section" aria-labelledby="sources-title">
      <SectionHead id="sources" number="05 · Sources" title="Papers and guidelines behind each choice" />
      <ReferenceList title="Papers and guidelines" references={PAPERS} />
      <ReferenceList title="Data, maps and fonts" references={DATA_SOURCES} />
      <ReferenceList title="Photos" references={PHOTO_SOURCES} />
    </section>
  )
}

/**
 * How it works (route /how-it-works). Task F10 builds it from the Figma frame "How it works"
 * (node 12:1385) and its notes (34:380): the intro with its section tabs, the pipeline, the
 * models, testing, limits and sources. The text lives in howItWorks/content.ts, to check
 * against the paper's final text; no formula is in the main text, only behind "Show the
 * formula" (howItWorks/formulas.tsx).
 *
 * Not as Figma: the pipeline section draws no numbers. Figma's three stat cards, weekly chart
 * and score table belong to the map and Compare models (F9 draws that chart and table), so the
 * page links to both and stays text, as the plan's Screens table says. An input still awaited
 * carries the amber badge (none since A13's counts arrived). Limits and sources go beyond Figma's few lines:
 * every limit the plan and Notes.md state, and every source the app's data comes from (U8).
 * F12: Sources also credits Home's photos and QCESD's counts, which check U8 asks for here too.
 */
export default function HowItWorks() {
  const current = useCurrentSection()
  return (
    <>
      <title>How it works · LEPTON</title>
      <SiteHeader />
      <main>
        <Intro current={current} />
        <Pipeline />
        <Models />
        <Testing />
        <Limits />
        <Sources />
      </main>
      <Footer />
    </>
  )
}
