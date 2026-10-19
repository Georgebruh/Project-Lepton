import { existsSync } from 'node:fs'
import { join, resolve } from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig, type Connect, type Plugin } from 'vite'

/**
 * F1: answer a request for a file under /data/ or /assets/ that does not exist with 404, as
 * Vercel does (vercel.json). Without this, Vite's dev and preview servers answer it with the
 * page (index.html) and 200, so fetch('/data/scores.json') before B10's real run would pass
 * its res.ok check and then fail to read the JSON.
 */
function missingFilesAre404(): Plugin {
  const answer404 =
    (folder: string): Connect.NextHandleFunction =>
    (req, res, next) => {
      const path = (req.url ?? '').split('?')[0]
      const isFile = path.startsWith('/data/') || path.startsWith('/assets/')
      if (isFile && !existsSync(join(folder, decodeURIComponent(path)))) {
        res.statusCode = 404
        res.end('Not found')
        return
      }
      next()
    }
  return {
    name: 'missing-files-are-404',
    // npm run dev serves the files in public/
    configureServer(server) {
      server.middlewares.use(answer404(server.config.publicDir))
    },
    // npm run preview serves the build in dist/
    configurePreviewServer(server) {
      server.middlewares.use(answer404(resolve(server.config.root, server.config.build.outDir)))
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), missingFilesAre404()],
})
