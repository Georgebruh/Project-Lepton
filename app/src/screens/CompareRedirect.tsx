import { Navigate, useLocation } from 'react-router'
import { COMPARE_PATH } from '../map/routes.ts'

/**
 * F14: /compare, the address of F9's Compare models screen, which the site header's Results and
 * How it works link to. Compare models is now a tab of the map's city panel, so this opens it
 * there, in Real data mode (results are about the real counts), keeping the address's ?period=.
 */
export default function CompareRedirect() {
  const params = new URLSearchParams(useLocation().search)
  params.set('data', 'real')
  return <Navigate to={`${COMPARE_PATH}?${params}`} replace />
}
