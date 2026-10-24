import { Outlet, ScrollRestoration } from 'react-router'

/** The root of every route: the current screen, in <Outlet />. */
export default function App() {
  return (
    <>
      <ScrollRestoration />
      <Outlet />
    </>
  )
}
