# D7 v3 무라벨 발화율 — Colab 실행 안내

상태: **GPU 미실행.** 준비만 끝났다. 이 문서는 실행 조작을 소유한다.
무엇을 왜 재는지는 [D7 보고서](README.md) §확인되지 않은 것이 소유한다.

## 왜 GPU 가 필요한가 — v5 와 갈리는 자리

| 항목 | 게이트가 읽는 것 | 무라벨 측정 |
| --- | --- | --- |
| v5 | 메타(적용계약법·업무구분·추정가격)뿐 | **CPU 로 끝난다.** 모델 불필요 |
| v3 | **모델이 낸 인용** 안의 실적 금액 | 무라벨에 모델 출력이 없다 → **GPU 회차** |

A4 §5 가 v6·v9 에서 한 "게이트가 보는 신호의 보유율"은 원문·메타만 보면 됐다.
v3 은 그 신호가 모델 출력 안에 있어서 같은 방법이 통하지 않는다.

## 고정 핀

- 실행 코드: **`c236a67244cc871a815084788493ec6d3f39d27e`** — 노트북 `REPO_REF` 에 이미 박혀 있다.
  `main` 이나 움직이는 브랜치로 바꾸지 않는다.
- 이 커밋은 **PR #96 의 v3 게이트 위에 쌓여 있다.** 재려는 대상이 그 게이트이고
  `performance_below_budget(rec, evidence)` 두 인자 서명이 거기에만 있다.
- 수집기: [experiments/d7_collect_v3_firing.py](../../../experiments/d7_collect_v3_firing.py)
  — [a5_collect_facts.py](../../../experiments/a5_collect_facts.py) 의 샤드·재개·계약 뼈대에서
  **호출 단계만** `company_size` → 24항목 기본 호출로 바꾼 것이다.
- 노트북: [notebooks/colab-d7-v3-firing.ipynb](../../../notebooks/colab-d7-v3-firing.ipynb)
  — [colab-a5-facts.ipynb `c24f2086`](https://colab.research.google.com/github/LittleBitAI/ai-nara-shop/blob/c24f20865cdc00ae6e01f2efac170bcfacef0436/notebooks/colab-a5-facts.ipynb)
  을 복제해 위 다섯 자리만 고쳤다.
- 모델: 고정 리비전 `4d7ae4984b7db7de8f8457170b3f1a419ee76d52`, Python 3.12.13 · vLLM 0.26.0.

## 필요한 것 둘

| 무엇 | 어디에 | 확인 |
| --- | --- | --- |
| `train_unlabeled.jsonl` | Google Drive `내 드라이브/d7/train_unlabeled.jsonl` | 790,790,220바이트 · 20,000건 · sha256 `f46449fb84f980a5ddf868d66f5daff2bcf0991135d9b81da5656dd607275698` |
| Colab Secret `HF_TOKEN` | 노트북 접근 허용 | 고정 모델 읽기 권한 |

원본은 Git 추적 제외라 clone 에 안 들어온다. 노트북이 해시와 건수를 직접 검사하고,
어긋나면 모델을 적재하기 전에 멈춘다.

## 실행

1. 노트북을 위 링크로 열고 **A100 GPU** 런타임을 고른다(VRAM 30GiB 이상·디스크 80GiB 이상 사전 검사).
2. 셀 1의 `REPO_REF` 가 위 40자리 SHA 인지 확인한다. 약칭이면 clone 뒤 검사에서 멈춘다.
3. 위에서부터 전부 실행한다. 기본값 `SHARDS_PER_EPISODE = 1` 을 유지한다 —
   첫 회차는 **dev 200건 + 무라벨 1,000건 표본**이다.
4. 마지막 셀이 내려주는 `d7-v3-firing-results-*.zip` 을 보관·전달한다. **실패했어도 그 셀은 실행한다.**
5. 이어서 재려면 같은 코드·GPU·Drive 폴더로 첫 셀부터 다시 실행한다. 완료된 묶음은 다시 안 돈다.

## 무엇이 나오나

`summary.json` 이 dev 와 무라벨 각각에서 셋을 센다.

| 값 | 뜻 |
| --- | --- |
| `model_v3_rate` | 모델이 v3=1 을 낸 비율 |
| `gate_fired_rate` | 그중 `performance_below_budget(rec, 근거문구)` 가 값을 돌려준 비율 = **게이트가 내리는 자리** |
| `gate_fired_given_model_v3` | 모델 양성 대비 게이트 발화 비율 |
| `final_v3_rate` | `postprocess` 까지 통과한 최종 v3 |
| `unlabeled_over_dev` | 위 세 비율의 **무라벨/dev 배율** — W5 가 요구하는 값 |

게이트에 넘기는 인용은 **정제 전 원 근거문구**다. `apply_qualification_rules` 가 보는 것과
같아야 발화율이 운영과 같은 뜻을 가진다.

**dev 쪽 기준값은 이미 있다.** 보관 회차 `colab-1789902969401579900` 의 기본 단계 원응답
200건을 같은 `observe()` 로 세면 모델 v3=1 **20건(10.0%)** · 게이트 발화 **10건(5.0%)** ·
최종 v3 **10건(5.0%)** 이다. 회차가 내는 dev 값이 이것과 크게 다르면 회차 churn 이 아니라
설정이 어긋난 것으로 읽는다.

## 시간과 한계

| | |
| --- | --- |
| dev 200건 실측(18f07e5 회차) | 677.1초 |
| 환산 1,000건 | 약 1시간 |
| 환산 20,000건 | 약 18.8시간 |

그래서 기본은 표본 한 묶음이다. `complete=true` 가 아닌 수치는 **표본이라고 적는다.**
회차당 7,200초 예보 검사가 걸려 있고, 넘길 것 같으면 완료된 묶음을 저장한 채 멈춘다.

이 측정은 **발화율이지 정확도가 아니다.** 배율이 낮으면 dev 이득이 비공개 집합에서 그대로
나오지 않는다는 경고이고, 높다고 그 이득이 서버로 간다는 증거도 아니다.
