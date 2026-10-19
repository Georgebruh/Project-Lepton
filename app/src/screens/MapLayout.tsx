import { Outlet } from 'react-router'

/**
 * The frame the three map levels share (routes /map, /map/quezon-city and
 * /map/quezon-city/prophylaxis). Task F4 puts the one MapLibre map here, so it stays on
 * screen while the level changes and the drill-down can animate: zoom, fade, panel slide
 * (Figma: the map drill-down section, node 53:267, and its notes, node 58:447). The level's
 * own content shows in <Outlet />.
 */
export default function MapLayout() {
  return <Outlet />
}
