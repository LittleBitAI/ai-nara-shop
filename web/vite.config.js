import { createReadStream } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 공고 원문과 정답 라벨은 저장소의 open/ 이 원본이다. 사본을 web/ 으로 복사하지 않는다 —
// 복사본은 원본이 바뀌면 조용히 갈린다. dev 서버가 그 자리에서 읽어 준다.
//
// 내보내는 것은 화면이 실제로 받아 가는 두 파일뿐이다. 경로를 받아 검사하는 방식은
// 쓰지 않는다 — 문자열 정규화와 접두사 비교는 심볼릭 링크·정션의 실제 대상을 안 본다.
// `open/leak` 를 저장소 밖으로 건 정션으로 밖의 파일이 그대로 나오는 것을 확인했다.
// 이름 두 개만 받으면 그 경로 자체가 없다.
const OPEN = fileURLToPath(new URL('../open/', import.meta.url))
const SERVED = new Map([
  ['dev.jsonl', 'application/x-ndjson'],
  ['dev_labels.csv', 'text/csv'],
])

function serveOpen() {
  return {
    name: 'serve-open',
    configureServer(server) {
      server.middlewares.use('/open', (req, res, next) => {
        const name = decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '')
        const type = SERVED.get(name)
        if (!type) {
          res.statusCode = 403
          return res.end(`내보내지 않는 경로다. 여기서 받는 것은 ${[...SERVED.keys()].join(', ')} 뿐이다`)
        }
        res.setHeader('content-type', type)
        createReadStream(join(OPEN, name)).on('error', next).pipe(res)
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), serveOpen()],
  server: { port: 5310, strictPort: false },
})
