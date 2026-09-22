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
// 값은 (내보낼 형식, **읽을 실제 경로**) 다. 키와 경로를 따로 두는 이유는 아래 둘이다.
const SERVED = new Map([
  ['dev.jsonl', { type: 'application/x-ndjson', file: 'dev.jsonl' }],
  ['dev_labels.csv', { type: 'text/csv', file: 'dev_labels.csv' }],
])

// 법령 전문 23개도 같은 규칙으로 연다 — **폴더를 읽어 실제 이름만** 목록에 넣는다.
// 경로를 받아 검사하는 방식으로 돌아가지 않는다. 이름이 목록에 없으면 그 경로 자체가 없다.
//
// **`isFile()` 인 것만 담는다.** 이름만 읽으면 그 폴더에 저장소 밖을 가리키는 `leak.txt`
// 링크를 둔 순간 목록이 그 이름을 그대로 받아들여, 이름 허용 목록으로 막아 둔 링크 탈출이
// 동적 목록에서 되살아난다. Dirent 의 `isFile()` 은 링크에 false 다.
// (이 기계에서는 파일 심볼릭 링크 생성이 EPERM 이라 실물 재현은 못 했다. 기제는
//  readdir 이 링크 이름을 그대로 주고 createReadStream 이 링크를 따라가는 것이다.)
//
// 키는 NFC 로 맞추고 **읽기는 원래 이름으로 한다.** macOS 는 readdir 이 NFD 로 주므로
// 정규화한 키로 열면 그 경로가 없다 — 화면이 부르는 이름과 디스크의 이름이 다르다.
for (const entry of readdirSync(join(OPEN, LAW_DIR), { withFileTypes: true })) {
  if (!entry.isFile() || !entry.name.endsWith('.txt')) continue
  SERVED.set(`${LAW_DIR}/${entry.name}`.normalize('NFC'),
             { type: 'text/plain; charset=utf-8', file: `${LAW_DIR}/${entry.name}` })
}

function serveOpen() {
  return {
    name: 'serve-open',
    configureServer(server) {
      server.middlewares.use('/open', (req, res, next) => {
        const name = decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '').normalize('NFC')
        const served = SERVED.get(name)
        if (!served) {
          res.statusCode = 403
          // 법령 23개까지 늘어놓으면 오류 메시지가 문단이 된다. 앞 둘과 개수만 적는다.
          return res.end(`내보내지 않는 경로다. 여기서 받는 것은 dev.jsonl, dev_labels.csv 와 `
                       + `${LAW_DIR}/ 의 법령 ${SERVED.size - 2}개뿐이다`)
        }
        res.setHeader('content-type', served.type)
        createReadStream(join(OPEN, served.file)).on('error', next).pipe(res)
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), serveOpen()],
  server: { port: 5310, strictPort: false },
})
