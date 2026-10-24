import { Fragment } from 'react'
import { Link } from 'react-router'
import Button from '../components/Button.tsx'
import Footer from '../components/Footer.tsx'
import Icon from '../components/Icon.tsx'
import SiteHeader from '../components/SiteHeader.tsx'
import BacktestChart from '../home/BacktestChart.tsx'
import {
  PREVIEW_NAME,
  loadCityForecast,
  loadPlanPreview,
  useLoaded,
  type Loaded,
  type PlanPreviewData,
} from '../home/homeData.ts'
import { HERO_PHOTO, STRIP_PHOTOS } from '../home/photos.ts'
import PlanPreview from '../home/PlanPreview.tsx'
import { WATERLINES } from '../home/waterlines.ts'
import { formatCount } from '../map/forecast.ts'
import CountUp from '../motion/CountUp.tsx'
import { useReveal } from '../motion/reveal.ts'
import './Home.css'

/** The hero photo's drawn width for srcSet. */
const HERO_SIZES = '(max-width: 1023px) 1200px, max(100vw, 1440px)'

/** The strip photos' drawn width: a third of the 1248 px content at most, the full width below 1024 px. */
const STRIP_SIZES = '(max-width: 1023px) 100vw, 400px'

/** The "How it's built" rows: the part, what it does, and its tag. */
const BUILT = [
  {
    name: 'Inputs',
    text: 'NASA IMERG and ECMWF rain, Project NOAH flood maps, WorldPop 100 m population, PSA census and births, the DOH facility registry, and QCESD weekly cases.',
    tag: 'Data',
  },
  {
    name: 'Flood exposure index',
    text: 'A storm’s 3-day rain over the city’s catchments, placed against its return levels, becomes the share of each barangay’s residents in flooded zones.',
    tag: 'Shared',
  },
  {
    name: 'City model',
    text: 'A negative binomial regression on season, recent cases, two weeks of rain and the exposure index, with the city’s population as an offset.',
    tag: 'Layer 1',
  },
  {
    name: 'Stock rules',
    text: 'DOH DM 2023-0309 regimens by risk tier for adults, plus children’s courses and amoxicillin for pregnant women.',
    tag: 'Layer 2',
  },
  {
    name: 'Testing',
    text: 'A week-by-week backtest from 2018 to 2026 with a leak check, mean absolute error as the primary score, and four real storms for the stock plan.',
    tag: 'Evidence',
  },
  // LEPTON is for the whole country, and why it starts in Quezon City (the paper's Scope)
  {
    name: 'Where it runs',
    text: 'Built for the whole Philippines: every input but the case counts already comes from national sources. Quezon City is first: the most populous city, with an up-to-date case list, and the one city there was time to ask for its counts while LEPTON was built.',
    tag: 'Scope',
  },
]

/** Home (route /). */
export default function Home() {
  const preview = useLoaded(loadPlanPreview)
  const forecast = useLoaded(loadCityForecast)
  const reveal = useReveal<HTMLElement>()
  return (
    <>
      <title>LEPTON · Leptospirosis forecasts for the Philippines, starting with Quezon City</title>
      <SiteHeader />
      <main ref={reveal} className="home">
        <section className="home-hero" aria-labelledby="home-hero-title">
          <img
            className="home-hero-photo"
            src={HERO_PHOTO.src}
            srcSet={HERO_PHOTO.srcSet}
            sizes={HERO_SIZES}
            width={HERO_PHOTO.width}
            height={HERO_PHOTO.height}
            alt={HERO_PHOTO.alt}
            fetchPriority="high"
          />
          <div className="home-hero-shade" />
          <svg className="home-hero-waterlines" viewBox="0 0 1440 680" preserveAspectRatio="none" aria-hidden="true">
            {WATERLINES.map(({ d, opacity }, i) => (
              <path key={i} className="home-hero-waterline" d={d} strokeOpacity={opacity} />
            ))}
          </svg>
          <div className="home-hero-content">
            <h1 id="home-hero-title" className="home-hero-title display-xl">
              <span>See the risk</span> <span>before the water rises.</span>
            </h1>
            <p className="home-hero-text body-l">
              LEPTON combines rain forecasts, flood hazard maps and population data to estimate leptospirosis
              risk barangay by barangay, one to three days ahead. Built for the whole Philippines, it starts in
              Quezon City.
            </p>
            <Button variant="ghost" to="/map" className="home-hero-button">
              Try LEPTON
            </Button>
          </div>
        </section>

        <section className="home-banner" aria-labelledby="home-banner-title">
          <div className="home-banner-text" data-reveal>
            <h2 id="home-banner-title" className="heading-m">
              Waded through floodwater?
            </h2>
            <p className="home-banner-subtitle body-m">
              Find out what to do and where your nearest health center is.
            </p>
          </div>
          <div className="home-banner-actions" data-reveal>
            <Button variant="secondary" to="/leptospirosis">
              About leptospirosis
            </Button>
            <Button icon="arrow-right" to="/exposed">
              I have been exposed to floodwater
            </Button>
          </div>
        </section>

        <section className="home-why" aria-label="Why it matters">
          <p className="home-why-lead body-xl" data-reveal>
            Every typhoon season, residents wade through floodwater to get home, to work and to school. One to two
            weeks later, leptospirosis cases peak, after the medicine that could have prevented them was needed.
          </p>
          <ul className="home-photos">
            {STRIP_PHOTOS.map((photo) => (
              <li key={photo.src} data-reveal>
                <figure className="home-photo">
                  {/* Keeps the photo's corners while it settles into place */}
                  <div className="home-photo-frame">
                    <img
                      className="home-photo-image"
                      src={photo.src}
                      srcSet={photo.srcSet}
                      sizes={STRIP_SIZES}
                      width={photo.width}
                      height={photo.height}
                      alt={photo.alt}
                      loading="lazy"
                    />
                  </div>
                  <figcaption className="home-photo-caption body-s">{photo.caption}</figcaption>
                </figure>
              </li>
            ))}
          </ul>
        </section>

        <section className="home-map" aria-labelledby="home-map-title">
          <h2 id="home-map-title" className="home-map-title heading-l" data-reveal>
            Pick a day, and LEPTON shows which barangays the rain will flood and what each health center should
            stock.
          </h2>
          <PlanPreview preview={preview} />
        </section>

        <section className="home-get" aria-label="What you get">
          <div className="home-get-column" data-reveal>
            <p className="home-get-eyebrow label-eyebrow">One to three days ahead</p>
            <h2 className="home-get-title heading-l">A stock list for every health center</h2>
            <p className="home-get-text body-l">
              Doxycycline for adults by DOH risk tier, children’s courses and amoxicillin for pregnant women, split to
              the nearest of the city’s {typeof preview === 'object' ? `${preview.needs.length} ` : ''}health
              centers.
            </p>
            <StockFigures preview={preview} />
          </div>
          <div className="home-get-column home-get-cases" data-reveal>
            <p className="home-get-eyebrow label-eyebrow">Next week</p>
            <h2 className="home-get-title heading-l">City cases, with a 90% range</h2>
            <p className="home-get-text body-l">
              Next week’s leptospirosis cases and the chance of crossing the epidemic threshold, so hospitals can
              prepare beds and staff.
            </p>
            <BacktestChart forecast={forecast} />
            <p className="home-get-note body-s">
              Scored every week from 2018 against a published Prophet–XGBoost model and two seasonal baselines.
            </p>
          </div>
        </section>

        <section className="home-built" aria-labelledby="home-built-title">
          <h2 id="home-built-title" className="home-built-title heading-l" data-reveal>
            How it’s built
          </h2>
          <ul className="home-built-rows">
            {BUILT.map(({ name, text, tag }) => (
              <li key={name} className="home-built-row" data-reveal>
                <h3 className="home-built-name heading-m">{name}</h3>
                <p className="home-built-text body-l">{text}</p>
                <p className="home-built-tag label-eyebrow">{tag}</p>
              </li>
            ))}
          </ul>
          <Link to="/how-it-works" className="home-built-more label-ui" data-reveal>
            Methods, limits and sources
            <Icon name="arrow-right" size={16} />
          </Link>
        </section>

        <section className="home-try" aria-labelledby="home-try-title">
          <div className="home-try-line" data-reveal>
            <div className="home-try-text">
              <h2 id="home-try-title" className="home-try-title display-xl">
                Try LEPTON
              </h2>
              {/* LEPTON is not live (live forecasts are future work); the map has every week of the backtest */}
              <p className="home-try-subtitle body-l">The latest forecast, or any week since 2018.</p>
            </div>
            <Link to="/map" className="home-try-go" aria-label="Try LEPTON: open the map">
              <Icon name="arrow-right" size={36} />
            </Link>
          </div>
        </section>
      </main>
      <Footer credits={<PhotoCredits />} />
    </>
  )
}

type StockFiguresProps = {
  /** Kristine's forecast 1 day ahead, while it loads undefined, or "failed". */
  preview: Loaded<PlanPreviewData>
}

/** Quezon City's stock for the previewed forecast. */
function StockFigures({ preview }: StockFiguresProps) {
  const data = typeof preview === 'object' ? preview : undefined
  const figures = [
    { name: 'Doxycycline 100 mg capsules', value: data?.flood.doxy100 },
    { name: 'Children’s courses', value: data?.flood.courses },
    { name: 'Amoxicillin 500 mg tablets', value: data?.flood.amox500 },
  ]
  let note = 'Loading the forecast…'
  if (preview === 'failed') {
    note = 'The stock figures could not load.'
  } else if (data) {
    const days = data.run.lead_days ?? 1
    const flood = data.flood.w === null ? `${data.flood.D}-day flood` : `${data.flood.D}-day flood, w = ${data.flood.w}`
    note = `Forecast ${days === 1 ? '1 day' : `${days} days`} before ${PREVIEW_NAME} · ${flood} · stock planning, not prescriptions`
  }
  return (
    <>
      <dl className="home-get-figures">
        {figures.map(({ name, value }) => (
          <div key={name} className="home-get-figure">
            <dt className="body-m">{name}</dt>
            <dd className="data-l">{value === undefined ? '—' : <CountUp value={value} format={formatCount} />}</dd>
          </div>
        ))}
      </dl>
      <p className="home-get-note body-s">{note}</p>
    </>
  )
}

/** The photos' credits for the footer: what each shows, its author and its licence, with links. */
function PhotoCredits() {
  const photos = [HERO_PHOTO, ...STRIP_PHOTOS]
  return (
    <>
      Photos from Wikimedia Commons, resized (the first also cropped):{' '}
      {photos.map(({ credit }, i) => (
        <Fragment key={credit.source}>
          <a href={credit.source} target="_blank" rel="noreferrer">
            {credit.title}
          </a>{' '}
          by {credit.author},{' '}
          <a href={credit.licenseUrl} target="_blank" rel="noreferrer">
            {credit.license}
          </a>
          {i < photos.length - 1 ? '; ' : '.'}
        </Fragment>
      ))}
    </>
  )
}
