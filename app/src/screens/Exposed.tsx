import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import ExposureCheck from '../exposed/ExposureCheck.tsx'
import { loadGuideData } from '../exposed/guideData.ts'
import { askForLocation, type Origin } from '../exposed/location.ts'
import NearestCenters from '../exposed/NearestCenters.tsx'
import { NO_ANSWERS, unanswered, type Answers, type QuestionKey } from '../exposed/risk.ts'
import YourResult from '../exposed/YourResult.tsx'

/**
 * The "I have been exposed to floodwater" guide, made for phones (route /exposed). Task F8
 * builds it from the Figma frames "1 Exposure check" (node 39:301), "2 Your result" (39:361) and
 * "3 Nearest health centers" (39:411), and the guide's notes beside them (40:356). Reads
 * /data/centers.json and /data/qc_barangays.geojson, written by F2, only at step 3.
 *
 * Answers and location never leave the phone: they live only in this screen's memory, so
 * nothing stores them and leaving the guide forgets them. The address holds only the step
 * (/exposed?step=2), so the phone's Back gesture goes back one step; a reloaded or shared
 * address past step 1 has no answers, and opens the questions.
 */
export default function Exposed() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [answers, setAnswers] = useState<Answers>(NO_ANSWERS)
  const [origin, setOrigin] = useState<Origin>({ kind: 'asking' })
  // Counts the requests for the phone's position, so only the latest one's answer counts
  const request = useRef(0)
  const titleRef = useRef<HTMLHeadingElement>(null)

  const answered = unanswered(answers).length === 0
  const asked = Number(searchParams.get('step'))
  const step = answered && (asked === 2 || asked === 3) ? asked : 1

  // A step past 1 without answers in memory: back to the questions, without a new history entry
  useEffect(() => {
    if (searchParams.has('step') && step === 1) {
      setSearchParams({}, { replace: true })
    }
  }, [searchParams, step, setSearchParams])

  // A new step starts at its title, so a screen reader reads it first (not on the first load)
  const shownStep = useRef(step)
  useEffect(() => {
    if (shownStep.current !== step) {
      shownStep.current = step
      titleRef.current?.focus({ preventScroll: true })
    }
  }, [step])

  /**
   * Back in the top bar: the step before, as the phone's own Back does. From step 1, the page
   * the reader came from, or Home when the guide was the first page opened (React Router
   * numbers the entries of this visit in history.state.idx, from 0).
   */
  function goBack() {
    const visited = (window.history.state as { idx?: number } | null)?.idx ?? 0
    if (step > 1 || visited > 0) {
      navigate(-1)
    } else {
      navigate('/')
    }
  }

  function answer(key: QuestionKey, value: string) {
    setAnswers((before) => ({ ...before, [key]: value }))
  }

  /** Asks the phone for its position; an answer to an older request, or after a pick, is dropped. */
  function locate() {
    const ask = ++request.current
    setOrigin({ kind: 'asking' })
    askForLocation((found) => {
      if (ask === request.current) {
        setOrigin(found)
      }
    })
  }

  /** "Find the nearest health center": the only place the guide asks for the phone's location. */
  function findCenters() {
    // Fetch the health centers while the phone looks for its position (step 3 shows any failure)
    loadGuideData()
    locate()
    setSearchParams({ step: '3' })
  }

  function pickBarangay(psgc: string) {
    request.current++
    setOrigin({ kind: 'barangay', psgc })
  }

  if (step === 1) {
    return (
      <ExposureCheck
        answers={answers}
        onAnswer={answer}
        onDone={() => setSearchParams({ step: '2' })}
        onBack={goBack}
        titleRef={titleRef}
      />
    )
  }
  if (step === 2) {
    return <YourResult answers={answers} onFindCenters={findCenters} onBack={goBack} titleRef={titleRef} />
  }
  return (
    <NearestCenters
      origin={origin}
      onUseLocation={locate}
      onPickBarangay={pickBarangay}
      onBack={goBack}
      titleRef={titleRef}
    />
  )
}
