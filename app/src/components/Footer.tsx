import type { ReactNode } from 'react'
import { Link } from 'react-router'
import Logo from './Logo.tsx'
import './Footer.css'

/** The project's code on GitHub. */
const GITHUB_URL = 'https://github.com/Georgebruh/Project-Lepton'

/**
 * The paper's public address. The Paper link stays hidden while this is null, so the footer
 * never shows a link that goes nowhere (check U7); set it once the paper is online.
 */
const PAPER_URL: string | null = null

type FooterProps = {
  /** The page's own credits, e.g. Home's photos: their authors, licences and links. */
  credits?: ReactNode
}

/**
 * F3: the footer, from the Figma frame "Home" (node 20:364): the logo, the team, links to the
 * code, the paper and the sources, and the stock-planning note that every dose figure needs.
 * F6: `credits` names the sources of what the page shows under the note, such as Home's
 * photos; check U8 wants every source credited in the footer and in How it works.
 */
export default function Footer({ credits }: FooterProps) {
  return (
    <footer className="footer">
      <div className="footer-row">
        <Logo />
        <p className="footer-team body-s">
          Team MANSCIT · University of the Philippines Cebu · PJDSC 2026
        </p>
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
      {credits && <p className="footer-credits body-s">{credits}</p>}
    </footer>
  )
}
