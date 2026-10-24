import { useCallback, useId, useRef, useState, type KeyboardEvent } from 'react'
import MapButton from './MapButton.tsx'
import { useOutsidePress } from './useOutsidePress.ts'
import './WordHelp.css'

/** A word the panel uses and what it means in plain words. */
export type Word = { term: string; meaning: string }

type WordHelpProps = {
  /** The open view's words, in the order the view shows them. */
  words: Word[]
}

/** The ? at the panel's lower right: it opens "What the words mean" upward from it. */
export default function WordHelp({ words }: WordHelpProps) {
  const id = useId()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const button = useRef<HTMLButtonElement>(null)
  const close = useCallback(() => setOpen(false), [])
  useOutsidePress(open, box, close)

  /** Escape closes the words, not the panel (MapLayout), and gives the keyboard back to the ?. */
  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape' && open) {
      event.preventDefault()
      setOpen(false)
      button.current?.focus()
    }
  }

  return (
    <div ref={box} className="word-help" onKeyDown={onKeyDown}>
      {open && (
        <section id={id} className="word-help-box" aria-labelledby={`${id}-title`}>
          <h3 id={`${id}-title`} className="heading-s">
            What the words mean
          </h3>
          <dl className="word-help-words">
            {words.map(({ term, meaning }) => (
              <div key={term} className="word-help-word">
                <dt className="label-ui">{term}</dt>
                <dd className="body-s">{meaning}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}
      <MapButton
        ref={button}
        icon="help"
        label="What the words mean"
        open={open}
        controls={id}
        onClick={() => setOpen(!open)}
      />
    </div>
  )
}
