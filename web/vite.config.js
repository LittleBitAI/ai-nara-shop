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

// 법령 전문 23개. **이름을 여기에 못 박는다 — 폴더에서 발견하지 않는다.**
//
// 한 번은 `readdirSync` 로 목록을 만들었다. 그러면 그 폴더에 `leak.txt` 를 둔 순간 목록이
// 그 이름을 받아들인다. `isFile()` 로 심볼릭 링크만 걸러도 소용이 없다 — **하드 링크는
// 권한 없이 만들어지고 `isFile()` 이 true 다.** 그냥 갖다 둔 파일도 마찬가지다. 즉 막아야 할
// 것은 링크의 종류가 아니라 **목록이 동적이라는 것**이다. 목록이 코드에 있으면 새 이름은
// 무엇이든 403 이고, 이 목록을 고치는 일은 diff 로 보인다.
//
// 제공 법령은 대회 입력 스냅샷이라 이름이 안 바뀐다. 폴더와 이 목록이 어긋나면
// `tests/test_build_report.py::test_served_law_names_match_the_package` 가 터진다.
const LAW_FILES = [
  '(계약예규) 공동계약운용요령.txt',
  '(계약예규) 정부 입찰·계약 집행기준.txt',
  '국가를 당사자로 하는 계약에 관한 법률 등의 재정경제부장관이 정하는 고시금액.txt',
  '국가를 당사자로 하는 계약에 관한 법률 시행규칙.txt',
  '국가를 당사자로 하는 계약에 관한 법률 시행령.txt',
  '국가를 당사자로 하는 계약에 관한 법률.txt',
  '소상공인기본법 시행령.txt',
  '소상공인기본법.txt',
  '소프트웨어 진흥법 시행령.txt',
  '소프트웨어 진흥법.txt',
  '중소 소프트웨어사업자의 사업 참여 지원에 관한 지침.txt',
  '중소기업기본법 시행령.txt',
  '중소기업기본법.txt',
  '중소기업자간 경쟁제품 및 공사용자재 직접구매 대상 품목 지정 내역.txt',
  '중소기업자간 경쟁제품 직접생산 확인기준.txt',
  '중소기업제품 구매촉진 및 판로지원에 관한 법률 시행규칙.txt',
  '중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령.txt',
  '중소기업제품 구매촉진 및 판로지원에 관한 법률.txt',
  '지방자치단체 입찰 및 계약 집행기준.txt',
  '지방자치단체 입찰시 낙찰자 결정기준.txt',
  '지방자치단체를 당사자로 하는 계약에 관한 법률 시행규칙.txt',
  '지방자치단체를 당사자로 하는 계약에 관한 법률 시행령.txt',
  '지방자치단체를 당사자로 하는 계약에 관한 법률.txt',
]

// 키는 NFC 다. **읽기는 디스크의 실제 이름으로 한다** — macOS 는 readdir 이 NFD 로 주므로
// 정규화한 이름으로 열면 그 경로가 없다. 그 김에 실물이 일반 파일인지도 여기서 본다.
//
// **정규화하면 같아지는 이름이 둘이면 연다는 판단 자체가 틀린 것이므로 시작을 멈춘다.**
// NFC 와 NFD 는 디스크에서 서로 다른 파일이고(NTFS 에서 둘 다 만들어지는 것을 확인했다),
// 맵으로 접으면 둘 중 어느 것이 허용된 URL 로 나갈지 **열거 순서**가 정한다. 집합 비교만
// 하는 검사도 이 중복을 못 본다. 조용히 다른 실물을 내보내느니 안 뜨는 편이 낫다.
const ON_DISK = new Map()
for (const entry of readdirSync(join(OPEN, LAW_DIR), { withFileTypes: true })) {
  if (!entry.isFile()) continue
  const key = entry.name.normalize('NFC')
  const twin = ON_DISK.get(key)
  if (twin !== undefined) {
    throw new Error(`${LAW_DIR} 에 정규화하면 같아지는 이름이 둘이다: `
                  + `${JSON.stringify(twin)} 와 ${JSON.stringify(entry.name)}. `
                  + '어느 것을 내보낼지 정할 수 없어 멈춘다.')
  }
  ON_DISK.set(key, entry.name)
}
for (const name of LAW_FILES) {
  const real = ON_DISK.get(name.normalize('NFC'))
  if (!real) continue                       // 스냅샷에 없는 이름은 안 연다
  SERVED.set(`${LAW_DIR}/${name}`.normalize('NFC'),
             { type: 'text/plain; charset=utf-8', file: `${LAW_DIR}/${real}` })
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
