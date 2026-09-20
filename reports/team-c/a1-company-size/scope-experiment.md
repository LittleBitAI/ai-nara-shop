# A1 scope 질문 단일변수 후보

2026-09-20. 상태: 로컬 후보 준비 완료, GPU·무라벨 실측·독립 리뷰 미실행.

## 가설과 범위

합본 `0a172a2`, 실제 회차 `colab-1789872032146524122`를 기준으로 한다.
`reports/team-c/competitive-gate/README.md`의 후속 측정에 따르면 경쟁제품 양성 합집합
15건 중 scope=competitive는 0건이다. 정확한 후보가 전달된 9건도 모두 general이다.
후보 부족만으로 설명할 수 없으므로 매칭기는 바꾸지 않는다.

구매 대상의 고시 적용 여부를 계약 절차명·직생/기업등급 요건의 존재와 분리해서 묻는다.
`COMPANY_SIZE_PROMPT`의 scope 설명만 변경한다. 공고의 실제 구매 대상과 제공 후보의
코드/의미·특이사항을 대조하고, 요건 부재나 빈 일치후보만으로 general을 고르지 않게 한다.
후보 존재 자체를 competitive 확정으로 만들지 않는다. other/unknown·원문 인용은 유지한다.
공고 ID·개별 dev 사례는 프롬프트에 넣지 않았다.

스키마·qualification 이하 지시·검색·문서 예산·호출 수·결정표·A2 정규식은 그대로다.
증명서 지시의 qualification 혼동과 v20은 별개 실험이며 이 후보에 넣지 않았다.
company_size scope는 현재 v14~v18만 바꾼다. v10/v11/v13에 연결하는 변경도 포함하지 않는다.

## 기준선 분리

작업 브랜치는 A1 단독 `4762271`이므로 그 script.py 전체를 합본에 덮어쓰면 안 된다.
작업본에는 scope hunk만 수정했다. 실행 후보는 다음과 같이 합본 코드에서 별도로 만들었다.

1. `git archive`로 `0a172a2`의 script.py·requirements·tools·tests·notebooks를
   `artifacts/a1-scope/integrated/`에 추출했다. open은 기존 제공 데이터에 연결했다.
2. 같은 scope hunk만 적용했다. 기준 파일에서 scope 블록만 후보 블록으로 치환한 결과가
   후보 전체 파일과 정확히 같음을 assert로 확인했다. HEAD 작업본에도 같은 검사를 했다.
3. 해당 폴더에서 기존 패키징 도구를 실행했다. 공유 브랜치 병합·커밋·push는 하지 않았다.
4. 주 작업공간 데이터의 CRLF 차이가 발견되어 첫 검증 번들을
   `rejected-crlf-colab-bundle.zip`으로 분리했다(실행 금지). 제출 ZIP은 그대로 두고,
   현재 워크트리의 입력·채점 도구가 모두 `git show 0a172a2:<경로>`와 바이트 단위로
   같음을 확인한 뒤 기존 `package_colab()`으로 최종 `colab-bundle.zip`을 다시 만들었다.
   공유 원본은 수정하지 않았다. 아래 번들 해시는 이 최종 파일이다.

```powershell
# artifacts/a1-scope/integrated 에서 실행
python -X utf8 -m unittest tests.test_company_size tests.test_package.PackageTests.test_colab_bundle_runs_exact_submission_and_rejects_bad_archive tests.test_package.PackageTests.test_diagnostic_run_is_on_by_default_and_refuses_a_silent_no_op -q
python -X utf8 tools/package.py --output ../6257404c/submit.zip --colab-output ../6257404c/colab-bundle.zip
```

## 로컬 검증 결과

- 위 관련 검사 9개 통과. 실패 보존·결정표·재생·실제 노트북 보호 검사·진단 기본값 포함.
- 패키지: 압축 해제 mock 샘플 10건·49열, 모델 없는 기본 진입 실패 확인.
- 합본 기준과 후보로 같은 최신 dev-debug 원응답 200건을 각각 재생했다.
  두 CSV와 보관 회차 CSV가 모두 바이트 단위로 같다. 프롬프트 성능 측정이 아니다.
- 작업본 `tests.test_company_size` 7개, ruff, git diff --check, UTF-8 no BOM·LF 통과.
- Python 3.13.9/Windows 로컬 검사이며 서버 Python 3.12.13/GPU 검증은 아니다.
- scope 설명은 436자에서 1,036자로 늘었다. 고정 모델 토크나이저가 로컬에 없어 실제
  입력 토큰·예산 축소·시간은 미측정이다. 회차의 company_size_input/max_chars와
  company_size_documents_shrunk를 기준선과 대조한다. mock 토큰 추정으로 대체하지 않는다.

| 파일 | SHA-256 |
| --- | --- |
| 합본 후보 script.py | `6257404c2fe1ce53836d11b1272c9e9ea77c6839cf2a2a28e999522a4bf5394b` |
| submit.zip | `5d12a3cbec5a733a28ac45553f1807616cea66a2d7f4a61a32e1541597c0c0ec` |
| colab-bundle.zip | `1f50faab96c01c9ccebd9f25121b21352f01e108e85217e3c58aea5cb6e1e839` |
| colab-baseline.ipynb | `559b664228af979d4872e5023ddbb42437dcdc41fee53ab39555fa12d19c1df0` |

## 실제 실행 방법과 채택 전 측정

`artifacts/a1-scope/6257404c/colab-baseline.ipynb`를 새로 연다.
첫 셀에서 **SOURCE_MODE="upload"**만 바꾸고 같은 폴더의 `colab-bundle.zip`을 올린다.
`REPO_REF`는 upload 모드에서 사용하지 않는다. `RUN_DIAGNOSTIC=True`,
`DIAGNOSE_ITEMS=""`는 유지한다. 이 후보는 미게시 상태라 clone 모드를 쓰면 후보가 아니다.
노트북은 0a172a2 판본이며 extra_call_items 기반 보호 검사가 들어 있다.

같은 ZIP으로 별도 회차를 한 번 더 실행하고 양쪽 결과 ZIP을 보관한다.
새 원응답이 생기면 scope 양성 회복을 후보 전달 9건/미일치 6건으로 나누고,
전체 competitive/unknown 건수·유효 인용·A1 TP/FP/FN·대상 밖 변화도 확인한다.
15건 밖을 scope 음성 정답으로 간주하지 않는다. scope 개수 증가만으로 채택하지 않는다.
v10/v11/v13 양성 집합은 scope 진단용이며 그 항목의 개선을 이번 후보 성과로 주장하지 않는다.

`tools/compare_runs.py`로 기준/후보 및 동일 ZIP 두 회차를 각각 비교한다.
역사적 churn 상한을 새 프롬프트의 허용선으로 쓰지 않는다.
무라벨 앞 6,000건은 별도 실제 모델 실행 후 `tools/company_size_canary.py`로 집계한다.
무라벨 발화율·실제 모델 점수·서버 시간은 현재 모두 미측정이다. 제출 후보 채택이 아니다.
