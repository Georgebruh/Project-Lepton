import { Link, isRouteErrorResponse, useRouteError } from 'react-router'
import './ErrorPage.css'

/**
 * F1: the page shown in place of a screen, for an address that is not one of the eight
 * screens (a 404) and for an error while drawing a screen, so a reader never sees a blank
 * page or a stack trace. The error itself goes to the browser's console.
 */
export default function ErrorPage() {
  const error = useRouteError()
  const notFound = isRouteErrorResponse(error) && error.status === 404
  return (
    <main className="error-page">
      <h1 className="heading-l">{notFound ? 'Page not found' : 'Something went wrong'}</h1>
      <p>
        {notFound ? 'There is no page at this address.' : 'This page could not be shown.'}{' '}
        <Link to="/">Go to the home page</Link>.
      </p>
    </main>
  )
}
