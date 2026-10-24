import { Fragment, type ReactNode } from 'react'
import { Link } from 'react-router'
import Logo from './Logo.tsx'
import './Footer.css'

/** The project's code on GitHub. */
const GITHUB_URL = 'https://github.com/Georgebruh/Project-Lepton'

/** One kind of data the app uses, and who it comes from: each source's name, link and licence. */
type Credit = { what: string; sources: { name: string; url?: string; license?: string }[] }

/** Every source of the app's data, maps and fonts, credited in the footer. */
const CREDITS: Credit[] = [
  {
    what: 'Boundaries',
    sources: [
      { name: 'PSA and NAMRIA via OCHA', url: 'https://data.humdata.org/dataset/cod-ab-phl', license: 'CC BY-IGO' },
      { name: 'J. Faeldon', url: 'https://github.com/faeldon/philippines-json-maps', license: 'MIT' },
    ],
  },
  {
    what: 'Flood maps',
    sources: [{ name: 'Project NOAH, UP Resilience Institute', url: 'https://noah.up.edu.ph', license: 'ODbL' }],
  },
  {
    what: 'Population',
    sources: [
      { name: 'WorldPop', url: 'https://doi.org/10.5258/SOTON/WP00839', license: 'CC BY 4.0' },
      {
        name: 'PSA, with its 2020 ages via OCHA',
        url: 'https://data.humdata.org/dataset/popn-single-year-age-sex-and-barangay-census-2020',
        license: 'CC BY',
      },
    ],
  },
  { what: 'Health centers', sources: [{ name: 'DOH National Health Facility Registry', url: 'https://nhfr.doh.gov.ph' }] },
  { what: 'Rain', sources: [{ name: 'NASA IMERG', url: 'https://doi.org/10.5067/GPM/IMERGDL/DAY/07' }] },
  {
    what: 'Rain forecasts and reanalysis',
    sources: [{ name: 'ECMWF and ERA5 via Open-Meteo', url: 'https://open-meteo.com', license: 'CC BY 4.0' }],
  },
  { what: 'Cases', sources: [{ name: 'Quezon City Epidemiology and Surveillance Division' }] },
  {
    what: 'Fonts',
    sources: [
      { name: 'Figtree', url: 'https://fonts.google.com/specimen/Figtree' },
      { name: 'Instrument Sans', url: 'https://fonts.google.com/specimen/Instrument+Sans', license: 'SIL OFL' },
    ],
  },
]

/** CREDITS as sentences: "Boundaries: PSA and NAMRIA via OCHA (CC BY-IGO) and J. Faeldon (MIT)." */
function DataCredits() {
  return (
    <>
      {CREDITS.map(({ what, sources }) => (
        <Fragment key={what}>
          {what}:{' '}
          {sources.map(({ name, url, license }, i) => (
            <Fragment key={name}>
              {i > 0 && ' and '}
              {url ? (
                <a href={url} target="_blank" rel="noreferrer">
                  {name}
                </a>
              ) : (
                name
              )}
              {license && ` (${license})`}
            </Fragment>
          ))}
          .{' '}
        </Fragment>
      ))}
    </>
  )
}

/** The paper's public address. */
const PAPER_URL: string | null = null

type FooterProps = {
  /** The page's own credits, e.g. Home's photos: their authors, licences and links. */
  credits?: ReactNode
}

/** The footer: logo, links to the code, paper and sources, and the stock-planning note. */
export default function Footer({ credits }: FooterProps) {
  return (
    <footer className="footer">
      <div className="footer-row">
        <Logo />
        <p className="footer-event body-s">PJDSC 2026</p>
        <nav className="footer-links" aria-label="Footer">
          <a href={GITHUB_URL} className="footer-link label-ui" target="_blank" rel="noreferrer">
            GitHub
          </a>
          {PAPER_URL && (
            <a href={PAPER_URL} className="footer-link label-ui" target="_blank" rel="noreferrer">
              Paper
            </a>
          )}
          <Link to="/how-it-works#sources" className="footer-link label-ui">
            Sources
          </Link>
        </nav>
      </div>
      <p className="footer-note body-s">
        Dose figures are for stock planning, not prescriptions. DOH DM 2023-0309 requires a
        physician’s consultation before any prophylaxis.
      </p>
      <p className="footer-credits body-s">
        <DataCredits />
      </p>
      {credits && <p className="footer-credits body-s">{credits}</p>}
    </footer>
  )
}
