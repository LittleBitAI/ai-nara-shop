---
scope: project
severity: preference
triggers: []
domain: ''
title: "feat: give the label comparison a blind bundle the answers cannot leak into"
pr: 26
merged: 2026-09-17
branch: "feat/a-label-compare"
---

# feat: give the label comparison a blind bundle the answers cannot leak into

무엇. 무라벨 20,000건에 붙일 라벨의 생성기를 고르기 위한 도구다. 외부 LLM 두 개(GPT 6.0 Astra와 Claude Opus 5)를 같은 프롬프트·같은 입력으로 dev 200건에 블라인드로 돌려 `open/dev_labels.csv` 대비 항목별 TP/FP/FN으로 비교한다. `tools/label_bundle. …

왜. 정답 누출이 이 작업의 제1 위험이다. CLI 에이전트를 저장소 안에서 돌리면 블라인드가 자동으로 깨진다. `open/dev_labels.csv`가 49열 정답을, `reports/team-score-audit/cases.jsonl`이 사례별 `"true"`·`"pred"`와 근거 span을 갖고 있고, 에이전트는 악의 없이도 문맥을 찾으려고 저장소를 뒤진다. 그래서 `export`는 저장소 안 경로를 거부하고, 번들에는 공고 본문·항목표·제공 법령 스냅샷 25개만 넣는다. 인코딩 사고를 실제로 밟았다. 첫 200건 실행이 전량 실패했다. 자식 프로세스가 cp949로 stdout을 내보내고 부모가 UTF-8로 읽어 한국어 키가 깨진 채 도착했는데, 에러는 `필드 불일치 ['... …

출처. PR #26 · `feat/a-label-compare`
