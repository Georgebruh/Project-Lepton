import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import ExposureCheck from '../exposed/ExposureCheck.tsx'
import { loadGuideData } from '../exposed/guideData.ts'
import { askForLocation, type Origin } from '../exposed/location.ts'
import NearestCenters from '../exposed/NearestCenters.tsx'
import { NO_ANSWERS, unanswered, type Answers, type QuestionKey } from '../exposed/risk.ts'
import YourResult from '../exposed/YourResult.tsx'

/** The "I have been exposed to floodwater" guide, made for phones (route /exposed). */
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

  // The step the reader came from (null on opening the guide), for its slide
  const [arrival, setArrival] = useState<{ step: number; from: number | null }>({ step, from: null })
  if (arrival.step !== step) {
    setArrival({ step, from: arrival.step })
  }

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

  /** Back in the top bar: the step before, as the phone's own Back does. */
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
        from={arrival.from}
        titleRef={titleRef}
      />
    )
  }
  if (step === 2) {
    return (
      <YourResult
        answers={answers}
        onFindCenters={findCenters}
        onBack={goBack}
        from={arrival.from}
        titleRef={titleRef}
      />
    )
  }
  return (
    <NearestCenters
      origin={origin}
      onUseLocation={locate}
      onPickBarangay={pickBarangay}
      onBack={goBack}
      from={arrival.from}
      titleRef={titleRef}
    />
  )
}
