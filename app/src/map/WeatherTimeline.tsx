import type { CSSProperties } from 'react'
import Badge from '../components/Badge.tsx'
import Icon from '../components/Icon.tsx'
import { ageOf, phtTime, type Frame } from './weather.ts'
import './WeatherTimeline.css'

type WeatherTimelineProps = {
  /** What the frames show, for screen readers: "Radar · live". */
  label: string
  /** The frames, oldest first. */
  frames: Frame[]
  /** The frame shown. */
  index: number
  /** Now (ms), for the frames' ages. */
  now: number
  playing: boolean
  onPlay: (on: boolean) => void
  onFrame: (index: number) => void
}

/**
 * F13: the live weather layer's timeline, Figma "Weather timeline" (Paused, Playing): play or
 * pause, the previous and next frame, a slider over the frames, the frame's time in Philippine
 * time and its age, and a badge saying the layer is now, not the map's date. It stands at the
 * bottom left of the map in sight (MapLayout). The slider is a native range input, so the arrow
 * keys move it and screen readers hear each frame's time.
 */
export default function WeatherTimeline({ label, frames, index, now, playing, onPlay, onFrame }: WeatherTimelineProps) {
  const last = frames.length - 1
  const time = frames[index].time
  const played = { '--weather-timeline-played': `${last > 0 ? (index / last) * 100 : 100}%` } as CSSProperties
  return (
    <div className="weather-timeline" role="group" aria-label={`${label}: timeline`}>
      <button
        type="button"
        className="weather-timeline-play"
        aria-label={playing ? 'Pause' : 'Play'}
        onClick={() => onPlay(!playing)}
      >
        <Icon name={playing ? 'pause' : 'play'} size={18} />
      </button>
      <div className="weather-timeline-steps">
        <button
          type="button"
          className="weather-timeline-step"
          aria-label="Previous frame"
          onClick={() => onFrame(index > 0 ? index - 1 : last)}
        >
          <Icon name="chevron-left" size={18} />
        </button>
        <button
          type="button"
          className="weather-timeline-step"
          aria-label="Next frame"
          onClick={() => onFrame(index < last ? index + 1 : 0)}
        >
          <Icon name="chevron-right" size={18} />
        </button>
      </div>
      <input
        type="range"
        className="weather-timeline-slider"
        style={played}
        min={0}
        max={last}
        value={index}
        aria-label="Frame"
        aria-valuetext={phtTime(time)}
        onChange={(event) => onFrame(Number(event.target.value))}
      />
      <p className="weather-timeline-when">
        <span className="label-ui">{phtTime(time)}</span>
        <span className="weather-timeline-age body-s">
          Frame {index + 1} of {frames.length} · {ageOf(time, now)}
        </span>
      </p>
      <Badge tone="accent" className="weather-timeline-live">
        <span className="weather-timeline-live-long">Live: now, not the map's date</span>
        <span className="weather-timeline-live-short">Live</span>
      </Badge>
    </div>
  )
}
