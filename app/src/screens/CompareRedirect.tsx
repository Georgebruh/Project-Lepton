import { Navigate } from 'react-router'

/**
 * /compare and /map/quezon-city/compare, Compare models' old addresses. It has left the map's panel and is to
 * move into How it works; until then they open How it works' Models part, as the site header's Results does.
 */
export default function CompareRedirect() {
  return <Navigate to="/how-it-works#models" replace />
}
