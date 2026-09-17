---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: 추론 실패 진단 보존 및 Colab 제출 코드 검증"
pr: 1
merged: 2026-09-16
branch: "docs/codex-t1-diagnosis"
---

# fix: 추론 실패 진단 보존 및 Colab 제출 코드 검증

무엇. 서버 제출이 `정상 모델 응답 재시도 실패 (ValueError)`로 중단될 때 원인 메시지와 생성 정보가 사라지던 문제를 보완합니다. 실패에도 실행 설정·자산 해시·공고 위치·최초/재시도별 종료 사유와 토큰 수·원인 traceback을 JSONL로 보존합니다.

왜. Colab은 HF_TOKEN으로 고정 리비전 모델을 준비한 뒤 실제 제출 ZIP의 코드를 서버처럼 무인자 `python script.py`와 PPS 경로로 실행합니다. Python·핵심 패키지·기본 추론 설정·ZIP 일치를 검사하고 샘플/dev 검증 및 채점 통과 후 같은 제출 ZIP을 내려받습니다. 검증: baseline 9개, package/Colab 경로 3개, score 4개 통과. mock 샘플 10건/dev 200건, ZIP 압축 해제 실행, 노트북 문법/nbformat, Ruff·diff 검사 통과. 실제 Colab GPU 실행과 서버 재제출은 미실행이며 비공개 입력·GPU/메모리·서버 전체 시간 차이로 서버 성공을 보장하지 않습니다. 사용자 지시로 독립 리뷰를 생략합니다. …

출처. PR #1 · `docs/codex-t1-diagnosis`
