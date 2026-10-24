import Icon from './Icon.tsx'
import './PanelHeader.css'

type PanelHeaderProps = {
  /** The section's title, e.g. "Layers". */
  title: string
  /** Whether the section under the header is open. */
  expanded: boolean
  /** Called when the header is clicked, to open or close the section. */
  onToggle: () => void
}

/** The "Panel header" component: the title of a section in a side panel, with a chevron. */
export default function PanelHeader({ title, expanded, onToggle }: PanelHeaderProps) {
  return (
    <button type="button" className="panel-header" aria-expanded={expanded} onClick={onToggle}>
      {/* Points down while open (PanelHeader.css) */}
      <Icon name="chevron-right" size={16} className="panel-header-chevron" />
      <span className="panel-header-title heading-s">{title}</span>
    </button>
  )
}
