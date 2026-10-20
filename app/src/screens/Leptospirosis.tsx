import type { ReactNode } from 'react'
import { Link } from 'react-router'
import Badge from '../components/Badge.tsx'
import Button from '../components/Button.tsx'
import SiteHeader from '../components/SiteHeader.tsx'
import './Leptospirosis.css'

/**
 * The pages each fact on this page comes from, numbered in the order the page first cites
 * them. Every medical fact links to its DOH source (F7); the team checks each one against it
 * before launch. DOH's own site turns away scripts, so its pages were read on 20 Oct 2026
 * through the Internet Archive (the disease page as of 11 June 2025).
 */
const SOURCES = [
  {
    id: 'doh-disease',
    title: 'Department of Health, “Leptospirosis” (list of diseases)',
    url: 'https://doh.gov.ph/list-of-diseases/leptospirosis/',
  },
  {
    id: 'doh-2024-07-24',
    title: 'Department of Health, press release, 24 July 2024: “DOH on Code White; leptospirosis has prophylaxis”',
    url: 'https://doh.gov.ph/press-release/doh-on-code-white-leptospirosis-has-prophylaxis/',
  },
  {
    id: 'doh-2024-08-07',
    title:
      'Department of Health, press release, 7 August 2024: “DOH lists more cases but less deaths for dengue; on guard for leptospirosis as rainy season continues”',
    url: 'https://doh.gov.ph/press-release/doh-lists-more-cases-but-less-deaths-for-dengue-on-guard-for-leptospirosis-as-rainy-season-continues/',
  },
  {
    id: 'doh-dm-2023-0309',
    title:
      'Department of Health, Department Memorandum 2023-0309 (14 August 2023): Guidelines on the Prevention, Control, Management, and Surveillance of Leptospirosis, Table 1 and section II.B (copy shared by DOH Center for Health Development XII)',
    url: 'https://drive.google.com/file/d/1fsclOOUcv04_vcHMefdkltFq3IkivuYo/view',
  },
  {
    id: 'qc-helpline',
    title: 'Quezon City Government, “QC Helpline 122”',
    url: 'https://quezoncity.gov.ph/program/qc-helpline-122/',
  },
  {
    id: 'pia-bandages',
    title: 'Philippine Information Agency, “DOH warns of leptospirosis risk as floods persist”',
    url: 'https://pia.gov.ph/disaster-information-service/doh-warns-of-leptospirosis-risk-as-floods-persist/',
  },
] as const

type SourceId = (typeof SOURCES)[number]['id']

/** A source's number on the page: its place in SOURCES, counting from 1. */
function sourceNumber(id: SourceId) {
  return SOURCES.findIndex((source) => source.id === id) + 1
}

/**
 * The hero's photo, or null for none. Figma's is AI-generated and no AI image ships (check
 * U7), so the hero shows its text alone until a real, licensed photo arrives (F6 finds Home's).
 * Then put the file in src/assets/, import it here as `src` with its `alt` text and `credit`,
 * and the photo and its credit appear (check U8).
 */
const HERO_PHOTO: { src: string; alt: string; credit: string } | null = null

/** The three key facts under the hero. */
const KEY_FACTS: { value: string; text: string; sources: SourceId[] }[] = [
  {
    value: '24–48 hours',
    text: 'DOH advises getting checked within this time after wading through floodwater.',
    sources: ['doh-2024-08-07'],
  },
  {
    value: '2 to 30 days',
    text: 'from exposure to the first symptoms; usually 1 to 2 weeks.',
    sources: ['doh-2024-08-07'],
  },
  {
    value: 'No wound needed',
    text: 'Wading alone can infect you, through the eyes, nose or mouth.',
    sources: ['doh-disease'],
  },
]

/** How you get it: the three ways in. */
const WAYS: { title: string; text: string; sources: SourceId[] }[] = [
  {
    title: 'Floodwater and wet soil',
    text: 'Water or mud mixed with the urine of infected animals, especially rats.',
    sources: ['doh-disease', 'doh-2024-07-24'],
  },
  {
    title: 'Through the skin',
    text: 'Cuts, scratches and soaked skin let the bacteria in, so wading with a wound raises your risk.',
    sources: ['doh-disease', 'doh-2024-07-24', 'doh-dm-2023-0309'],
  },
  {
    title: 'Through eyes, nose and mouth',
    text: 'Splashed or swallowed floodwater can infect you even if your skin has no wounds.',
    sources: ['doh-disease'],
  },
]

/** Signs that need a doctor soon. */
const EARLY_SIGNS = [
  'Fever, chills and headache',
  'Muscle pain, often in the calves',
  'Red eyes',
  'Nausea, vomiting or stomach pain',
]

/** Signs of severe leptospirosis, which need a hospital now. */
const SEVERE_SIGNS = [
  'Yellow skin or eyes',
  'Little or dark urine',
  'Bleeding, or coughing up blood',
  'Trouble breathing',
]

/**
 * DM 2023-0309 Table 1's three groups, in plain words: a single exposure with no break in the
 * skin; a wound or water in the eyes, nose or mouth; repeated or continuous exposure. The
 * memo names the first "mild"; DOH's advisories and this page call it low risk.
 */
const RISK_LEVELS = [
  {
    tone: 'accent',
    label: 'Low risk',
    text: 'You waded through floodwater once and had no cuts or wounds.',
  },
  {
    tone: 'warn',
    label: 'Moderate risk',
    text: 'You waded once with a cut or wound, or floodwater got into your eyes, nose or mouth.',
  },
  {
    tone: 'alert',
    label: 'High risk',
    text: 'You waded more than once, or stayed in floodwater for a long time — for example, living in a flooded area or helping with cleanup.',
  },
] as const

/** Protect yourself: four tips. */
const TIPS: { title: string; text: string; sources: SourceId[] }[] = [
  {
    title: 'Avoid wading',
    text: 'Stay out of floodwater whenever you can.',
    sources: ['doh-disease', 'doh-dm-2023-0309'],
  },
  { title: 'Wear boots and gloves', text: 'Especially during cleanup.', sources: ['doh-disease'] },
  {
    title: 'Cover wounds',
    text: 'Use a waterproof bandage before going out.',
    sources: ['pia-bandages'],
  },
  {
    title: 'Wash right away',
    text: 'Clean skin with soap and clean water after any contact.',
    sources: ['doh-disease', 'doh-dm-2023-0309'],
  },
]

/** The numbered links after a fact, e.g. [1][2]; each jumps to its entry under Sources. */
function Cite({ sources }: { sources: readonly SourceId[] }) {
  return (
    <sup className="leptospirosis-cite label-ui-s">
      {sources.map((id) => {
        const n = sourceNumber(id)
        return (
          <a key={id} href={`#source-${n}`} aria-label={`Source ${n}`}>
            [{n}]
          </a>
        )
      })}
    </sup>
  )
}

/** A section with Figma's heading over a rule; `id` names it for screen readers. */
function Section({ id, title, children }: { id: string; title: ReactNode; children: ReactNode }) {
  return (
    <section className="leptospirosis-section" aria-labelledby={id}>
      <h2 id={id} className="leptospirosis-section-head heading-m">
        {title}
      </h2>
      {children}
    </section>
  )
}

/** A list of signs with square bullets, teal or red (`alert`). */
function SignList({ signs, alert }: { signs: string[]; alert?: boolean }) {
  return (
    <ul className={alert ? 'leptospirosis-signs-list is-alert' : 'leptospirosis-signs-list'}>
      {signs.map((sign) => (
        <li key={sign} className="body-l">
          {sign}
        </li>
      ))}
    </ul>
  )
}

function Hero() {
  return (
    <section className="leptospirosis-hero" aria-labelledby="leptospirosis-title">
      <div className="leptospirosis-hero-text">
        <p className="leptospirosis-eyebrow label-eyebrow">For residents · Leptospirosis</p>
        <h1 id="leptospirosis-title" className="display-l">
          Waded through floodwater?
          <br />
          Get checked early.
        </h1>
        <p className="leptospirosis-lead body-l">
          Floodwater can carry leptospirosis from the urine of infected rats and other animals.
          <Cite sources={['doh-disease', 'doh-2024-07-24']} /> A health center can check you and
          decide if you need preventive medicine, before you get sick.
          <Cite sources={['doh-2024-08-07']} />
        </p>
        <div className="leptospirosis-actions">
          <Button icon="arrow-right" to="/exposed">
            I have been exposed to floodwater
          </Button>
          <Button variant="secondary" href="tel:122">
            Call QC Helpline 122
          </Button>
        </div>
      </div>
      {HERO_PHOTO && (
        <figure className="leptospirosis-hero-photo">
          <img src={HERO_PHOTO.src} alt={HERO_PHOTO.alt} />
          <figcaption className="body-s">{HERO_PHOTO.credit}</figcaption>
        </figure>
      )}
    </section>
  )
}

function KeyFacts() {
  return (
    <ul className="leptospirosis-facts" aria-label="Key facts">
      {KEY_FACTS.map(({ value, text, sources }) => (
        <li key={value} className="leptospirosis-fact">
          <p className="data-xl">{value}</p>
          <p className="leptospirosis-fact-text">
            {text}
            <Cite sources={sources} />
          </p>
        </li>
      ))}
    </ul>
  )
}

function Signs() {
  return (
    <Section id="leptospirosis-signs" title="Signs to watch for in the next 4 weeks">
      <div className="leptospirosis-signs">
        <div className="leptospirosis-signs-card">
          <h3 className="heading-m">
            Early signs: see a doctor
            <Cite sources={['doh-disease']} />
          </h3>
          <SignList signs={EARLY_SIGNS} />
        </div>
        <div className="leptospirosis-signs-card is-alert">
          <h3 className="leptospirosis-signs-alert-title heading-m">
            Go to a hospital now
            <Cite sources={['doh-disease', 'doh-2024-07-24', 'doh-dm-2023-0309']} />
          </h3>
          <SignList signs={SEVERE_SIGNS} alert />
          <p className="leptospirosis-note">
            Call QC Helpline 122 for emergencies, 24/7.
            <Cite sources={['qc-helpline']} />
          </p>
        </div>
      </div>
    </Section>
  )
}

function RiskLevels() {
  return (
    <Section
      id="leptospirosis-risk"
      title={
        <>
          Your risk level, as the Department of Health groups it
          <Cite sources={['doh-dm-2023-0309']} />
        </>
      }
    >
      <ul className="leptospirosis-risk">
        {RISK_LEVELS.map(({ tone, label, text }) => (
          <li key={label} className="leptospirosis-risk-level">
            <div className="leptospirosis-risk-badge">
              <Badge tone={tone}>{label}</Badge>
            </div>
            <p className="leptospirosis-risk-text body-l">{text}</p>
            <Link to="/exposed" className="leptospirosis-risk-action label-ui">
              Visit a health center
            </Link>
          </li>
        ))}
      </ul>
      <p className="leptospirosis-note">
        Whatever your level, a doctor decides if you need preventive medicine. Don’t take
        antibiotics without a consultation.
        <Cite sources={['doh-dm-2023-0309']} />
      </p>
    </Section>
  )
}

function ExposedCta() {
  return (
    <section className="leptospirosis-cta" aria-labelledby="leptospirosis-cta-title">
      <div className="leptospirosis-cta-line">
        <div className="leptospirosis-cta-text">
          <h2 id="leptospirosis-cta-title" className="display-l">
            Been in floodwater recently?
          </h2>
          <p className="body-l">Answer five quick questions and find your nearest health center.</p>
        </div>
        <Button icon="arrow-right" to="/exposed">
          I have been exposed to floodwater
        </Button>
      </div>
    </section>
  )
}

/** Figma's closing line, then the numbered sources the facts link to. */
function PageFooter() {
  return (
    <footer className="leptospirosis-footer body-s">
      <p>General information, not a diagnosis. Only a doctor can decide on treatment.</p>
      <h2 className="label-eyebrow">Sources</h2>
      <ol className="leptospirosis-sources">
        {SOURCES.map(({ id, title, url }) => (
          <li key={id} id={`source-${sourceNumber(id)}`}>
            <a href={url} target="_blank" rel="noreferrer">
              {title}
            </a>
          </li>
        ))}
      </ol>
    </footer>
  )
}

/**
 * Leptospirosis, for residents (route /leptospirosis). Task F7 builds it from the Figma frame
 * "Leptospirosis" (node 38:277) and its notes (40:338): plain words for residents, whose main
 * action is the "I have been exposed to floodwater" button (/exposed, F8). The medical text
 * follows DOH's advisories and DM 2023-0309's low, moderate and high risk groups. It never
 * gives doses, and says a doctor decides on preventive medicine, as the memo requires.
 *
 * Changes from the frame's text, so every fact matches its source: incubation "2 to 30 days,
 * usually 1 to 2 weeks" (DOH, 7 Aug 2024; Figma had 2 days to 4 weeks, usually 7 to 10);
 * "infected animals, especially rats" (no DOH source names dogs or pigs); "Fever", not
 * "Sudden fever"; high risk is the memo's repeated or continuous exposure (Figma's "two days or
 * more" is LEPTON's own cut-off, config.py); "a doctor decides", not "a doctor or nurse"
 * (the memo requires a physician). Each fact's source links sit after it as [n].
 */
export default function Leptospirosis() {
  return (
    <>
      <title>Leptospirosis · LEPTON</title>
      <SiteHeader />
      <main>
        <Hero />
        <KeyFacts />
        <Section id="leptospirosis-ways" title="How you get it">
          <div className="leptospirosis-ways">
            {WAYS.map(({ title, text, sources }) => (
              <div key={title} className="leptospirosis-way">
                <h3 className="heading-s">{title}</h3>
                <p className="leptospirosis-way-text body-l">
                  {text}
                  <Cite sources={sources} />
                </p>
              </div>
            ))}
          </div>
        </Section>
        <Signs />
        <RiskLevels />
        <Section id="leptospirosis-protect" title="Protect yourself">
          <ul className="leptospirosis-tips">
            {TIPS.map(({ title, text, sources }) => (
              <li key={title} className="leptospirosis-tip">
                <h3 className="heading-s">{title}</h3>
                <p className="leptospirosis-tip-text">
                  {text}
                  <Cite sources={sources} />
                </p>
              </li>
            ))}
          </ul>
        </Section>
        <ExposedCta />
      </main>
      <PageFooter />
    </>
  )
}
