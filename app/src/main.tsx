// The app's entry point.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router/dom'
import './styles/tokens.css'
import './styles/global.css'
import './styles/motion.css'
import { CAMERA_MS, CROSSFADE_MS, EASE_CSS, HOVER_MS } from './map/motion.ts'
import { router } from './router.tsx'

// The map's motion values, for every screen's CSS (styles/motion.css)
const root = document.documentElement.style
root.setProperty('--motion-hover', `${HOVER_MS}ms`)
root.setProperty('--motion-enter', `${CAMERA_MS}ms`)
root.setProperty('--motion-crossfade', `${CROSSFADE_MS}ms`)
root.setProperty('--motion-ease', EASE_CSS)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
