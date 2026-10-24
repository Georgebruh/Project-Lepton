import { Navigate, useLocation } from 'react-router'
import { COMPARE_PATH } from '../map/routes.ts'

/** /compare, the address of the Compare models screen. */
export default function CompareRedirect() {
  const params = new URLSearchParams(useLocation().search)
  params.set('data', 'real')
  return <Navigate to={`${COMPARE_PATH}?${params}`} replace />
}
