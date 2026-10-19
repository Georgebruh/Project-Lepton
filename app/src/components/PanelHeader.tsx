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

/**
 * F3: the Figma component "Panel header" (node 4:17): the title of a section in a side panel,
 * with a chevron. Clicking it opens or closes the section. Figma draws only the open state
 * (chevron down); closed shows chevron-right, from the same icon set.
 */
export default function PanelHeader({ title, expanded, onToggle }: PanelHeaderProps) {
  return (
    <button type="button" className="panel-header" aria-expanded={expanded} onClick={onToggle}>
      <Icon name={expanded ? 'chevron-down' : 'chevron-right'} size={16} />
      <span className="panel-header-title heading-s">{title}</span>
    </button>
  )
}
