// F1: the app's entry point. The design tokens and base styles load before the screens:
// when two rules are equally specific, the later one wins, so a screen's own CSS can adjust
// a text-style class.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router/dom'
import './styles/tokens.css'
import './styles/global.css'
import { router } from './router.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
