#!/usr/bin/env bash
# 회차 진단 화면을 띄운다. macOS 는 Finder 에서 더블클릭, 그 밖에서는 ./report.command 로 실행한다.
# Windows 는 report.cmd 를 쓴다. 두 파일이 하는 일은 같다.
#
#   ./report.command              받은 함의 가장 최근 결과 ZIP을 채점하고 띄운다
#   ./report.command --all        등록된 회차 전부 다시 만들고 띄운다
#   ./report.command --run <id>   그 회차만
#
# ZIP 파일명은 회차마다 바뀐다. 여기에 이름을 적지 않고 --latest 가 고른다.

set -u

# 더블클릭하면 Terminal 이 홈 디렉터리에서 열린다. 저장소는 이 파일의 자리에서 찾는다.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || exit 1

# 이름이 잡히는 것과 실제로 도는 것은 다르다. Windows 의 Store 별칭도, macOS 의 끊긴
# Xcode 심 링크도 `command -v` 는 통과하고 실행은 아무것도 안 한다. 한 번 돌려 본다.
PY=""
for candidate in python3 python; do
  command -v "$candidate" >/dev/null 2>&1 || continue
  "$candidate" -c 'import sys' >/dev/null 2>&1 || continue
  PY="$candidate"
  break
done
[ -n "$PY" ] || { echo "쓸 수 있는 python3 이 없다. 먼저 깐다: https://python.org"; exit 1; }

# 순서 로직은 tools/report.py 한 곳이다. report.cmd 와 여기가 서로 베끼지 않는다.
exec "$PY" -X utf8 tools/report.py "$@"
