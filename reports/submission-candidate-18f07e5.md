# 제출 후보 `18f07e5` — 기록할 항목을 미리 채워 둔다

2026-09-20. 아직 제출하지 않았다. 제출은 사용자가 대회 화면에서 한다.
제출한 뒤 결과 두 칸(`outcome`·`leaderboard_macro_f1`·`elapsed_seconds`)만 채우면
`reports/submissions.json`의 `submissions` 배열에 그대로 들어간다.

## 올릴 파일

`artifacts/inbox/submit.zip` — 44,100바이트.
이 파일이 Colab이 검증한 바로 그 ZIP이다. 다시 만들지 않는다.

| 대조 | 값 | 출처 |
| --- | --- | --- |
| ZIP sha256 | `8f3677a56e6b9fcb30f998b6ead02bb5351285c3eea244b437787502af069aa5` | `validation.json`·`manifest.json`과 일치 |
| 안의 `script.py` sha256 | `1691e8cc2e3a94c7af8a7dec703e58616dcc05337e633283630318ee69ac2a5b` | `git show 18f07e5:script.py`와 일치 |
| 회차 검사 | `colab_pass` · `quality_pass=true` | `validation.json` |

## `reports/submissions.json`에 넣을 항목

```json
{
  "submitted_on": "2026-09-20",
  "code_commit": "18f07e5cd9446500aa92bf254e104d4a8f5123dd",
  "script_sha256": "1691e8cc2e3a94c7af8a7dec703e58616dcc05337e633283630318ee69ac2a5b",
  "submit_zip_sha256": "8f3677a56e6b9fcb30f998b6ead02bb5351285c3eea244b437787502af069aa5",
  "run_id": "colab-1789902969401579900",
  "outcome": "<제출 뒤 채운다: scored | run_error>",
  "leaderboard_macro_f1": null,
  "elapsed_seconds": null,
  "elapsed_reported": null,
  "error": null,
  "source": "사용자 보고 (대회 화면)",
  "note": "A3 부재탐지 회차 5. v10·v18·v20이 같은 회차에서 처음 동시에 TP>0을 냈다. 첫 제출 5506ca0이 실행 오류로 채점되지 않아 남은 운영 확인 목적도 겸한다.",
  "dev_macro_f1_same_zip": 0.599315859077856,
  "dev_minus_leaderboard": null,
  "predicted_leaderboard": null
}
```

**`predicted_leaderboard`를 비워 둔다.** 전이율은 관측 두 쌍뿐이고
0.5%(654c556)에서 24.9%(57761ff)로 19%p 움직였다. 그 둘로 세 번째를 예측하는 것은
사후 설명이지 예측이 아니다. 제출 결과가 나온 뒤 `dev_minus_leaderboard`에 실측만 적는다.

## 제출 전 확인

| 항목 | 값 |
| --- | --- |
| 하루 제출 한도 | 1회 (`docs/rules.md` R16). 마지막 제출 2026-09-18 → 오늘 1회 가능 |
| 서버 시간 한도 | 7,200초 |
| 예측 실행 시간 | 6,396 ~ 6,571초 (한도의 88.8~91.3%) |
| 예측 근거 | dev 추론 3.583초/건 × 1,853 = 6,638초, 서버 실측 2점의 보정 계수 0.963~0.990 |
| 과거 최고 사용률 | `654c556` 6,192초 = 86.0% (완주) |

### 예측 모델의 근거

| 커밋 | dev 추론 초/건 | 1,853 환산 | 서버 실측 | 계수 |
| --- | ---: | ---: | ---: | ---: |
| `654c556` | 3.469 | 6,427 | 6,192 | 0.963 |
| `57761ff` | 2.334 | 4,325 | 4,281 | 0.990 |

관측 2점뿐이다. 오차 4%를 얹으면 최악 6,834초(94.9%)이고 그래도 한도 안이지만
여유가 366초로 줄어든다. 비공개 1,853건의 공고 길이 분포가 dev 200건과 다르면 흔들린다.

### 이 회차의 시간 분해 (dev 200건)

```
기본 호출        361.3초 / 200건
sme              108.2초 / 106건
company_size     247.0초 / 200건   ← 57761ff 에는 없던 단계
─────────────────────────────────
추론 합          716.5초 · 모델 적재 192초 · 총 913초
```

## 제출 뒤에 할 것

1. 대회 화면의 실행 시간을 `elapsed_seconds`·`elapsed_reported`에 적는다.
2. `outcome`·`leaderboard_macro_f1`을 적는다.
3. `dev_minus_leaderboard = 0.599315859077856 − 실측`을 계산해 적는다.
4. `dev_versus_leaderboard` 배열에 한 줄 더한다.
5. `.wiki/plan-active.md`의 dev 실측 이력표에 서버 열을 채운다.

실행 오류로 채점되지 않으면 `outcome: "run_error"`와 화면의 오류 문자열을
`error`에 그대로 적는다. 첫 제출 `5506ca0`이 그 경우였고 원인을 확정하지 못했다.

## 이 문서가 결정하지 않는 것

제출 여부는 사용자가 정한다. 사용자가 정한 정책은 "dev 0.70 전에는 점수 목적의
제출을 하지 않는다"이고 현재 dev는 0.599316으로 미달이다. 다만 첫 제출이
채점되지 않아 운영 확인 목적 제출 1회가 9/29 10:00 전에 별도로 필요하다.
이 문서는 올리기로 정했을 때 손이 멈추지 않도록 값만 미리 채워 둔 것이다.
