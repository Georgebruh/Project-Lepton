import { Outlet, ScrollRestoration } from 'react-router'

/**
 * F1: the root of every route: the current screen, in <Outlet />. ScrollRestoration opens each
 * new page at its top, and puts the old position back when the reader goes back. A setting
 * kept only in the address's query, such as F4's forecast week, should pass
 * { preventScrollReset: true } to setSearchParams, or every change jumps to the top.
 */
export default function App() {
  return (
    <>
      <ScrollRestoration />
      <Outlet />
    </>
  )
}
