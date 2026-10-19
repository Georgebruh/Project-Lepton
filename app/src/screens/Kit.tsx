import { useState, type ReactNode } from 'react'
import { useSearchParams } from 'react-router'
import AppBar from '../components/AppBar.tsx'
import Badge from '../components/Badge.tsx'
import Button from '../components/Button.tsx'
import CenterRow from '../components/CenterRow.tsx'
import Footer from '../components/Footer.tsx'
import Icon from '../components/Icon.tsx'
import { ICON_NAMES } from '../components/iconShapes.tsx'
import Logo from '../components/Logo.tsx'
import PanelHeader from '../components/PanelHeader.tsx'
import SiteHeader from '../components/SiteHeader.tsx'
import StatCard from '../components/StatCard.tsx'
import Tab from '../components/Tab.tsx'
import ToggleRow from '../components/ToggleRow.tsx'
import './Kit.css'

/** The three themes in tokens.css. Clinic is the app's; Monsoon is the Figma Components page's. */
const THEMES = [
  { id: 'clinic', name: 'Clinic' },
  { id: 'monsoon', name: 'Monsoon' },
  { id: 'ember', name: 'Ember' },
]

type KitSectionProps = {
  /** The component's name, as in Figma. */
  title: string
  /** Where it is in Figma, e.g. "Components · 3:65". */
  node: string
  /** Wide sections (the headers and the footer) fill the page with no padding. */
  wide?: boolean
  children: ReactNode
}

/** One component's variants, laid out as on the Figma Components page: 16 px padding and gaps. */
function KitSection({ title, node, wide = false, children }: KitSectionProps) {
  return (
    <section className="kit-section">
      <h2 className="kit-section-title">
        <span className="heading-s">{title}</span>
        <span className="data-m kit-node">Figma {node}</span>
      </h2>
      <div className={wide ? 'kit-set kit-set-wide' : 'kit-set'}>{children}</div>
    </section>
  )
}

/**
 * F3: the component kit (route /kit). It shows every shared component in
 * app/src/components/, in every variant, with Figma's sample text, so each one can be checked
 * against its Figma component side by side at 100% zoom. The Figma Components page is drawn
 * in the Monsoon theme, so the theme switch at the top applies Monsoon (or Ember) to this
 * page; the choice is kept in the address (?theme=monsoon). Not a screen of the app: nothing
 * links here.
 */
export default function Kit() {
  const [searchParams, setSearchParams] = useSearchParams()
  const theme = searchParams.get('theme') ?? 'clinic'
  const [toggleA, setToggleA] = useState(true)
  const [toggleB, setToggleB] = useState(false)
  const [layersOpen, setLayersOpen] = useState(true)

  function chooseTheme(id: string) {
    setSearchParams(id === 'clinic' ? {} : { theme: id }, { preventScrollReset: true })
  }

  return (
    <div className="kit" data-theme={theme === 'clinic' ? undefined : theme}>
      <header className="kit-intro">
        <p className="label-eyebrow kit-node">F3 · not a screen of the app</p>
        <h1 className="heading-l">Component kit</h1>
        <p className="body-m kit-text">
          Every shared component in app/src/components/, in every variant, with Figma’s sample
          text. The Figma Components page is drawn in Monsoon: choose Monsoon here and compare
          each component with Figma side by side, both at 100% zoom.
        </p>
        <div className="kit-themes" role="group" aria-label="Theme">
          {THEMES.map(({ id, name }) => (
            <Tab key={id} selected={theme === id} onClick={() => chooseTheme(id)}>
              {name}
            </Tab>
          ))}
        </div>
      </header>

      <KitSection title="Icons" node="Components · icon/…">
        <ul className="kit-icons">
          {ICON_NAMES.map((name) => (
            <li key={name} className="kit-icon">
              <Icon name={name} />
              <span className="label-ui-s kit-node">{name}</span>
            </li>
          ))}
        </ul>
        <div className="kit-icon-sizes">
          <span className="label-ui-s kit-node">18 px</span>
          {ICON_NAMES.map((name) => (
            <Icon key={name} name={name} size={18} />
          ))}
        </div>
        <div className="kit-icon-sizes">
          <span className="label-ui-s kit-node">16 px</span>
          {ICON_NAMES.map((name) => (
            <Icon key={name} name={name} size={16} />
          ))}
        </div>
      </KitSection>

      <KitSection title="Logo" node="Components · 3:47">
        <Logo />
      </KitSection>

      <KitSection title="Button" node="Components · 3:65">
        <div className="kit-row">
          <Button variant="primary" icon="arrow-right">
            Try LEPTON
          </Button>
          <Button variant="secondary" icon="arrow-right">
            Try LEPTON
          </Button>
          <Button variant="ghost" icon="arrow-right">
            Try LEPTON
          </Button>
        </div>
        <div className="kit-row">
          <Button variant="primary">Try LEPTON</Button>
          <Button variant="secondary">Try LEPTON</Button>
          <Button variant="ghost">Try LEPTON</Button>
        </div>
      </KitSection>

      <KitSection title="Badge" node="Components · 3:78">
        <div className="kit-row">
          <Badge tone="neutral">Experimental</Badge>
          <Badge tone="accent">Experimental</Badge>
          <Badge tone="warn">Experimental</Badge>
          <Badge tone="alert">Experimental</Badge>
        </div>
      </KitSection>

      <KitSection title="Tab" node="Components · 3:83">
        <div className="kit-row">
          <Tab>Overview</Tab>
          <Tab selected>Overview</Tab>
        </div>
      </KitSection>

      <KitSection title="Toggle row" node="Components · 3:94">
        <div className="kit-toggle-rows">
          <ToggleRow label="Exposure share" on={toggleA} onChange={setToggleA} />
          <ToggleRow label="Exposure share" on={toggleB} onChange={setToggleB} />
        </div>
      </KitSection>

      <KitSection title="Stat card" node="Components · 4:8">
        <div className="kit-stat-card">
          <StatCard
            label="Residents exposed"
            value="425,192"
            caption="Severe Tropical Storm Kristine, Oct 2024 · observed rain"
          />
        </div>
      </KitSection>

      <KitSection title="Center row" node="Components · 4:12">
        <div className="kit-center-rows" role="table" aria-label="Health centers">
          <CenterRow name="Tatalon Health Center" doxycycline={92935} courses={8737} amoxicillin={1124} />
        </div>
      </KitSection>

      <KitSection title="Panel header" node="Components · 4:17">
        <div className="kit-panel-header">
          <PanelHeader
            title="Layers"
            expanded={layersOpen}
            onToggle={() => setLayersOpen(!layersOpen)}
          />
        </div>
      </KitSection>

      <KitSection title="Site header" node="Components · 4:21" wide>
        <SiteHeader />
      </KitSection>

      <KitSection title="App bar" node="Map · 1 Metro Manila · 55:319" wide>
        <AppBar />
      </KitSection>

      <KitSection title="Footer" node="Home · 20:364" wide>
        <Footer />
      </KitSection>
    </div>
  )
}
