---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: Colab에서 git clone으로 제출 ZIP 준비"
pr: 2
merged: 2026-09-16
branch: "fix/codex-colab-clone"
---

# fix: Colab에서 git clone으로 제출 ZIP 준비

무엇. Colab 검증이 로컬 ZIP 수동 업로드에 의존하던 흐름을 보완합니다. 기본 모드에서 공개 저장소를 git clone하고 실제 커밋 SHA를 기록한 뒤 기존 패키징 도구로 제출 ZIP/검증 번들을 생성합니다. 같은 ZIP 검증·HF_TOKEN 모델 준비·서버 무인자 실행·검증 ZIP 다운로드를 이어서 사용하며 특정 로컬 ZIP 업로드도 선택할 수 있습니다.

왜. 검증: tests/test_package.py 4개 통과. 로컬 Git main의 실제 clone→커밋 기록→패키징 코드 일치, 수동 업로드 경로 회귀 확인. Ruff·diff·UTF-8 without BOM/LF·nbformat 통과. 실제 Colab GPU 실행은 미검증입니다. 사용자 지시로 독립 리뷰를 생략하며 이전 커밋·PR·머지 요청의 후속 보완입니다.

출처. PR #2 · `fix/codex-colab-clone`
