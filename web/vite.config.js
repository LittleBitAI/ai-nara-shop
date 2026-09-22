import { createReadStream, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 공고 원문과 정답 라벨은 저장소의 open/ 이 원본이다. 사본을 web/ 으로 복사하지 않는다 —
// 복사본은 원본이 바뀌면 조용히 갈린다. dev 서버가 그 자리에서 읽어 준다.
//
// 내보내는 것은 화면이 실제로 받아 가는 이름들뿐이다. 경로를 받아 검사하는 방식은
// 쓰지 않는다 — 문자열 정규화와 접두사 비교는 심볼릭 링크·정션의 실제 대상을 안 본다.
// `open/leak` 를 저장소 밖으로 건 정션으로 밖의 파일이 그대로 나오는 것을 확인했다.
// 목록에 있는 이름만 받으면 그 경로 자체가 없다.
const OPEN = fileURLToPath(new URL('../open/', import.meta.url))
const LAW_DIR = 'data/법령패키지/법령'
const SERVED = new Map([
  ['dev.jsonl', 'application/x-ndjson'],
  ['dev_labels.csv', 'text/csv'],
])

// 법령 전문 23개도 같은 규칙으로 연다 — **폴더를 읽어 실제 이름만** 목록에 넣는다.
// 경로를 받아 검사하는 방식으로 돌아가지 않는다. 이름이 목록에 없으면 그 경로 자체가 없다.
// macOS 는 readdir 이 NFD 로 주고 화면은 NFC 로 부르므로 양쪽을 NFC 로 맞춘다.
for (const name of readdirSync(join(OPEN, LAW_DIR))) {
  if (name.endsWith('.txt')) SERVED.set(`${LAW_DIR}/${name}`.normalize('NFC'), 'text/plain; charset=utf-8')
}

function serveOpen() {
  return {
    name: 'serve-open',
    configureServer(server) {
      server.middlewares.use('/open', (req, res, next) => {
        const name = decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '').normalize('NFC')
        const type = SERVED.get(name)
        if (!type) {
          res.statusCode = 403
          // 법령 23개까지 늘어놓으면 오류 메시지가 문단이 된다. 앞 둘과 개수만 적는다.
          return res.end(`내보내지 않는 경로다. 여기서 받는 것은 dev.jsonl, dev_labels.csv 와 `
                       + `${LAW_DIR}/ 의 법령 ${SERVED.size - 2}개뿐이다`)
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
