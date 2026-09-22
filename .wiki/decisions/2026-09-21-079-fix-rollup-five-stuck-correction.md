---
scope: project
severity: preference
triggers: []
domain: ''
title: "docs: ROLLUP §4 의 \"다섯은 공통 원인 하나\" 를 정정한다"
pr: 79
merged: 2026-09-21
branch: "fix/rollup-five-stuck-correction"
---

# docs: ROLLUP §4 의 "다섯은 공통 원인 하나" 를 정정한다

무엇. #78 이 먼저 머지돼야 합니다. 이 문서가 astra 의 세 파일을 상대 경로로 가리킵니다.

왜. `#75`로 main에 들어간 `ROLLUP.md` §4에 주 세션의 틀린 주장이 있습니다. > 무변화 다섯(v10·v13·v18·v20·v24)은 원인이 하나로 모인다. 주 세션과 astra가 같은 질문을 독립으로 분석해 둘 다 반증했습니다. 오답 공고 합집합 65건에서 쌍별 교집합이 0~3건뿐이라, 같은 몇 공고의 한 실패가 다섯 점수를 만든다는 설명은 성립하지 않습니다. 그대로 두면 다음 세션이 사실로 읽습니다. 주 세션의 판은 버렸습니다(PR #77 종료, 브랜치 삭제). 이 주제는 #78의 세 문서가 소유합니다. ``` reports/team-c/a5-label-definition/five-stuck-analysis. …

출처. PR #79 · `fix/rollup-five-stuck-correction`
