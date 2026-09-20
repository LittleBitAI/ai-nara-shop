import { createReadStream } from 'node:fs'
import { join, normalize, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 공고 원문과 정답 라벨은 저장소의 open/ 이 원본이다. 사본을 web/ 으로 복사하지 않는다 —
// 복사본은 원본이 바뀌면 조용히 갈린다. dev 서버가 그 자리에서 읽어 준다.
const OPEN = fileURLToPath(new URL('../open/', import.meta.url))
const TYPES = { '.jsonl': 'application/x-ndjson', '.csv': 'text/csv' }

function serveOpen() {
  return {
    name: 'serve-open',
    configureServer(server) {
      server.middlewares.use('/open', (req, res, next) => {
        const name = decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '')
        const file = normalize(join(OPEN, name))
        if (!file.startsWith(OPEN.replace(/[\\/]$/, '') + sep)) {
          res.statusCode = 403
          return res.end('밖으로 나가는 경로')
        }
        res.setHeader('content-type', TYPES[file.slice(file.lastIndexOf('.'))] ?? 'text/plain')
        createReadStream(file).on('error', next).pipe(res)
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), serveOpen()],
  server: { port: 5310, strictPort: false },
})
