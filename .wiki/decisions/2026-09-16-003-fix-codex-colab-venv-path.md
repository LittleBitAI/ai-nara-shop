---
scope: project
severity: preference
triggers: []
domain: ''
title: "fix: Colab venv 실행 경로 전달 및 ninja 사전 검사"
pr: 3
merged: 2026-09-16
branch: "fix/codex-colab-venv-path"
---

# fix: Colab venv 실행 경로 전달 및 ninja 사전 검사

무엇. Colab에서 ninja가 설치되어 있어도 venv 실행 경로가 PATH에 없어 FlashInfer 초기화가 실패했습니다. 공통 실행기가 venv Python 명령에 PATH와 VIRTUAL_ENV를 전달하고, 모델 다운로드 전에 ninja 실행 경로와 버전을 검사합니다.

왜. 검증: 기존 함수에서 실제 자식 프로세스 FileNotFoundError 재현, 수정 후 노트북·패키징 검사 5개 통과. Ruff·nbformat·UTF-8/LF·diff 검사 통과. 수정 후 실제 GPU 실행은 미확인입니다. 사용자 지시로 독립 리뷰를 생략합니다.

출처. PR #3 · `fix/codex-colab-venv-path`
