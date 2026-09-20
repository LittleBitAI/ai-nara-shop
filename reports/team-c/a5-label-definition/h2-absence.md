# A5 H2 — 관측된 기업규모 제한 부재를 v11에 연결

2026-09-21 · 상태: CPU 후보 검증 완료, **채택 보류**.
사용자가 승인한 다음 단계: 기존 company_size의 역할·완전관측·인용 검사를 통과한
기업규모 제한 부재만 v11에 전달한다. [H1](README.md)의 표기 확대는 포함하지 않는다.

## 변경과 근거

[후보](../../../experiments/a5_v11_absence_candidate.py)는 기존 `verify_company_size()`의 결과에
v11 양성만 추가한다. 다음 조건이 모두 필요하다.

- `scope=competitive`, `qualification=unrestricted`.
- 역할이 `none`, `checklist`, `legal_reference` 중 하나이며 등급 분류와 모순되지 않음.
- `qualification_complete=yes`, `requirements_complete=yes`, 입력 완전관측,
  문서 탈락·실제 입력 절단 없음.
- scope와 qualification 두 인용이 실제 관측 문서의 원문과 일치함. 기존 공백 복원을 재사용.
- 관측 사실의 예외가 `priority_exception=no`, `size_exception=none`으로 확인됨.

조건이 부족하면 기존 판정을 보존한다. 부재탐지의 e11은 비운다.
새 정규식으로 문서의 부재를 추정하지 않고 저장된 모델의 명시적 부재 관측을 소비한다.
법적 근거는 제공 판로지원법 제7조①이며, 직생 요구 문장이 있어야 v11이 적용된다는
조건은 그 조문에 없다. `docs/items.md`의 부재탐지 의미와 `docs/data.md` D4-5를 유지한다.

기존 scope-wiring 실험은 `scope=competitive + SME_ALLOWED 정규식 불일치`였고 FP가 15건이었다.
이번 후보는 그 정규식을 쓰지 않고 **H4의 역할·기업제한 부재 사실을 추가 검증**하므로
같은 가설의 재실행이 아니다. 그렇더라도 모델의 scope 오류까지 해결하는 것은 아니다.

## 같은 원응답 대조

기준 HEAD `734b4ec`, H4 `dev-debug` 원응답 200건. [HEAD 재생](head-replay/submission.csv)과
[H2 재생](absence-replay/submission.csv)을 `compare_runs.py --items v11`로 비교했다.

| 측정 | HEAD → H2 |
| --- | --- |
| v11 TP / FP / FN | **2/3/4 → 4/4/2** |
| v11 F1 | **0.363636 → 0.571429** |
| Macro F1 | **0.593846165415 → 0.602504174073** |
| 바뀐 셀 | v11 3셀, 다른 23항목 **0셀** |
| 새 TP | PPS-DEV-061, PPS-DEV-062 |
| 새 FP | PPS-DEV-040 |

[비교 원본](absence-comparison/comparison.json), [24항목 재채점](absence-score/metrics.json).
동일 원응답이므로 후보 효과에 추론 churn이 없다. **0.602504는 CPU 재생 값**이며
새 실제 GPU dev 점수·서버 점수·목표 0.70 달성으로 기록하지 않는다.

040의 scope 인용은 `2026년 모범이장 해외 선진지연수 용역`이다. 본문은 해외연수·여행업
자격을 요구한다. 사업명 인용이 실제라고 확인해도 경쟁제품 판별의 정확성까지 검증되지는
않는다. 이번 FP는 그 한계를 드러낸다. 이 한 건을 지우는 ID·여행업 예외는 추가하지 않았다.

060은 여전히 FN이다. 저장 모델은 직생 증명서 조항을 인용하면서 `sme_allowed`라고
분류했다. 064도 SW 사업자 요건을 기업등급 근거로 인용한다. **이번 후보는 이러한 잘못된
등급을 부재로 뒤집지 않는다.** 이 두 건은 별도의 사실 추출 수정이 필요하다.

## 무라벨·시간·채택 한계

H2 조건은 dev에서 **3/200(1.5%)** 발화했다. 무라벨 입력 20,000건은 있지만,
그 입력의 **company_size 모델 원응답이 없다**. 저장소의 실행 보고서를 확인했으며
200건 초과 실행 기록도 없었다. H4의 `dev/`, `sample/` 역시 원응답이 없어 추가 corpus로
재생할 수 없다.

따라서 H2의 무라벨 발화 **건수·비율·dev 대비 배율은 모두 미측정**이다.
H1 정규식의 0.8225배나 입력 완전관측 비율로 대신하지 않는다.
dev 이득은 확인했으나 이 통과 조건이 남아 있어 **운영 코드 채택은 보류**한다.

추가 모델 호출 **0회**, 프롬프트·스키마 변경 없음. §5 선계산의 서버 실측 6,380초와
여유 820초를 유지하며, 새 전건 호출은 넣지 않았다. 현재 호스트의 HEAD/H2 CPU 재생을
순서를 번갈아 5쌍 실행해 각 CSV가 기준 산출물과 바이트 동일한지 확인했다.
시간 목록·중앙값은 [absence-audit.json](absence-audit.json)에 기록했다.
CPU 재생 초를 GPU 추론 환산식에 넣거나 서버 총시간 실측으로 읽지 않는다.

**이 후보의 dev 효과를 재려는 Colab 재실행은 필요 없다.** 채택 전 남은 것은 무라벨에 대한
기존 모델의 관측 사실이다. 사용자 요청으로 [GPU 실행본과 절차](run-request.md)를 준비했다.
첫 회차는 기존 company_size로 dev 200건 + 무라벨 1,000건을 수집하고 Drive에서 재개한다.
새 dev 관측은 동일 수집 조건의 발화율 기준이며 새 F1 측정이 아니다. 전체 20,000건 완료 전에는
무라벨 통과로 세지 않는다. **GPU 실제 실행은 아직 안 했다.** 공용 제출 노트북이 아니라
전용 `colab-a5-facts.ipynb`를 사용하며 제출 ZIP을 만들지 않는다.

## 검증

- 변경 전: 061의 저장 사실을 기존 검증기에 전달해도 v11이 반환되지 않는 assert 실패 재현.
- 후보 self-check: 정상 부재, 등급·역할 모순, 불완전·문서 절단·누락, 잘못된 인용,
  예외 미확정, e11, 다른 항목 보존, 활성 재생 모듈 선택 통과.
- 기존 관련 검사: `pytest -q tests/test_replay_run.py tests/test_company_size.py tests/test_competitive_product.py`
  **31 passed (9.19초)**. H1 때 기록한 설치 검사 실패를 해결했다고 주장하지 않는다.
- HEAD/H2 재생·채점·3셀 비교 및 5쌍 바이트 동일 검사 통과.
- 원응답·입력·후보 해시는 `absence-audit.json`에 보존했다.

`script.py`·A3·A4 수정, 새 모델 호출, 독립 리뷰, 커밋·push·PR·merge·서버 제출은 하지 않았다.
H2는 유효한 CPU 개선 후보이며 일반화 검증이 끝난 채택본은 아니다.
