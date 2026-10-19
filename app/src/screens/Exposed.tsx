import Placeholder from './Placeholder.tsx'

/**
 * The "I have been exposed to floodwater" guide, made for phones (route /exposed). Task F8
 * builds it from the Figma frames "1 Exposure check" (node 39:301), "2 Your result"
 * (39:361) and "3 Nearest health centers" (39:411). Reads /data/centers.json, written by F2.
 */
export default function Exposed() {
  return <Placeholder screen="Exposure guide" task="F8" />
}
