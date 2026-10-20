import { useId, useImperativeHandle, useRef, useState, type KeyboardEvent, type ReactNode, type Ref } from 'react'
import PanelHeader from '../components/PanelHeader.tsx'
import './MapList.css'

/** One row of the list: a city or a barangay. */
export type MapListItem = {
  /** Its PSGC. */
  id: string
  /** Its name, as the row and the search by typing read it. */
  name: string
  /** What the row shows at its right end: a level badge, a share, "No data yet". */
  detail?: ReactNode
  /** What a screen reader hears after the name, e.g. "Low chance of an outbreak, 24 cases expected next week". */
  words: string
  /** Whether Enter (or a click) opens it: a city with a forecast. */
  opens?: boolean
}

/** What a level can do with its list: move the keyboard to it (MapLayout, after Back). */
export type MapListHandle = { focus: () => void }

type MapListProps = {
  /** What the rows are: "Cities", "Barangays". */
  title: string
  items: MapListItem[]
  /** Shown above the rows: a badge, the order of the rows. */
  note?: ReactNode
  /** How the keyboard works here, shown under the rows and read out with the list. */
  instructions: string
  /** Shows a row's city or barangay on the map, as the pointer would; null when none is shown. */
  onShow: (id: string | null) => void
  /** Opens a row whose `opens` is true. */
  onOpen?: (id: string) => void
  ref?: Ref<MapListHandle>
}

/** A name as the search by typing compares it: lower case, without accents ("Doña" is "dona"). */
function plain(name: string): string {
  return name.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

/** How long, in ms, keys typed one after another still add to the same search. */
const TYPING_MS = 700

/**
 * F11: the list beside the map that reaches every city (level 1) and barangay (level 3) without
 * a mouse, as the app plan asks; Figma has no frame for it. A Panel header (Figma 4:17) opens and
 * closes it; it starts closed, so the map looks as in Figma. Open, it is a listbox: Tab reaches
 * it, the arrow keys, Home, End or typing a name move through it, and the row reached shows its
 * place on the map with its tooltip, as hovering does. Enter opens a city with a forecast;
 * Escape closes the list. A screen reader hears each row's name and numbers (`words`).
 */
export default function MapList({ title, items, note, instructions, onShow, onOpen, ref }: MapListProps) {
  const id = useId()
  const [expanded, setExpanded] = useState(false)
  const [activeId, setActiveId] = useState<string | null>(null)
  const toggle = useRef<HTMLDivElement>(null)
  const listbox = useRef<HTMLUListElement>(null)
  const typed = useRef({ text: '', at: 0 })
  const active = items.find((item) => item.id === activeId) ?? items[0]

  useImperativeHandle(ref, () => ({
    focus() {
      const target = expanded ? listbox.current : toggle.current?.querySelector('button')
      target?.focus({ preventScroll: true })
    },
  }))

  /** Makes a row the active one, shows it on the map and scrolls it into the list's view. */
  function activate(item: MapListItem) {
    setActiveId(item.id)
    onShow(item.id)
    document.getElementById(`${id}-${item.id}`)?.scrollIntoView({ block: 'nearest' })
  }

  function onKeyDown(event: KeyboardEvent<HTMLUListElement>) {
    if (!active) {
      return
    }
    const at = items.indexOf(active)
    const moves: Record<string, number> = { ArrowDown: at + 1, ArrowUp: at - 1, Home: 0, End: items.length - 1 }
    if (event.key in moves) {
      event.preventDefault()
      activate(items[Math.max(0, Math.min(items.length - 1, moves[event.key]))])
    } else if (event.key === 'Enter') {
      if (active.opens) {
        event.preventDefault()
        onOpen?.(active.id)
      }
    } else if (event.key === 'Escape') {
      event.preventDefault()
      setExpanded(false)
      onShow(null)
      // The list is gone: the keyboard goes back to the header that opens it
      requestAnimationFrame(() => toggle.current?.querySelector('button')?.focus())
    } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
      // Typing a name jumps to the first row that starts with what was typed
      const now = Date.now()
      const text = (now - typed.current.at < TYPING_MS ? typed.current.text : '') + plain(event.key)
      typed.current = { text, at: now }
      const match = items.find((item) => plain(item.name).startsWith(text))
      if (match) {
        event.preventDefault()
        activate(match)
      }
    }
  }

  return (
    <div className={expanded ? 'map-list map-list-open' : 'map-list'}>
      <div ref={toggle}>
        <PanelHeader
          title={`${title} · ${items.length}`}
          expanded={expanded}
          onToggle={() => {
            setExpanded(!expanded)
            onShow(null)
          }}
        />
      </div>
      {expanded && (
        <>
          {note && <div className="map-list-note">{note}</div>}
          <ul
            ref={listbox}
            className="map-list-items"
            role="listbox"
            tabIndex={0}
            aria-label={title}
            aria-describedby={`${id}-instructions`}
            aria-activedescendant={active ? `${id}-${active.id}` : undefined}
            onKeyDown={onKeyDown}
            onFocus={() => active && onShow(active.id)}
            onBlur={() => onShow(null)}
          >
            {items.map((item) => (
              <li
                key={item.id}
                id={`${id}-${item.id}`}
                role="option"
                aria-selected={item === active}
                className="map-list-option"
                onClick={() => {
                  activate(item)
                  if (item.opens) {
                    onOpen?.(item.id)
                  }
                }}
              >
                <span className="map-list-name label-ui">
                  {item.name}
                  <span className="visually-hidden">: {item.words}</span>
                </span>
                {item.detail && (
                  <span className="map-list-detail" aria-hidden="true">
                    {item.detail}
                  </span>
                )}
              </li>
            ))}
          </ul>
          <p id={`${id}-instructions`} className="map-list-instructions body-s">
            {instructions}
          </p>
        </>
      )}
    </div>
  )
}
