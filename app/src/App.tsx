import { Outlet, ScrollRestoration } from 'react-router'
import { useSmoothInPageLinks } from './motion/smoothLinks.ts'

/** The root of every route: the current screen, in <Outlet />. */
export default function App() {
  useSmoothInPageLinks()
  return (
    <>
      <ScrollRestoration />
      <Outlet />
    </>
  )
}
