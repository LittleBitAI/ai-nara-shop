# 무라벨 삭제 집합 D — GPU 회차

[설계 감사](../unlabeled-design-audit.md) 8절의 "다음" 1번이다. v3·v17 삭제 후보가 무라벨에서 지우는 셀을
만들기 위해 운영 `script.py` 를 무라벨 표본에 그대로 돌린다. 제출용이 아니고 서버 시간 한도와 무관하다.

## 고정한 것

| 무엇 | 값 |
| --- | --- |
| 표본 순서 | [ids.txt](ids.txt), seed 20260923, 이미 라벨을 연 40건 제외 후 19,960건을 섞은 앞 6,000개. [manifest](ids.manifest.json) |
| 이번 범위 | 앞 2,000건, 500건씩 4묶음 |
| 실행 코드 | `14f03d1d5426920cdb9ca7af55e482a3ed1c777e` — 노트북 `REPO_REF` 에 박혀 있다 |
| 입력 | `train_unlabeled.jsonl` SHA-256 `f46449fb…`, 20,000건 |
| 노트북 | [colab-unlabeled-d.ipynb](../../../notebooks/colab-unlabeled-d.ipynb) |

## Colab 에서

1. 노트북을 Colab 에서 연다(GitHub 탭 또는 파일 업로드). 런타임은 A100.
2. `MyDrive/a5/train_unlabeled.jsonl` 이 있는지 확인한다. A5 때 올린 파일이다. 없으면 PC 의
   `open/train_unlabeled.jsonl` 을 Drive 내 드라이브 → a5 폴더에 올린다.
3. 보안 비밀 `HF_TOKEN` 에 노트북 접근을 허용한다.
4. 런타임 → 모두 실행. 예상 약 2시간 30분(dev 건당 3.56초 단순 환산).
5. 끊기면 첫 셀부터 다시 모두 실행한다. Drive `MyDrive/a5/unlabeled-d-14f03d1d5426/` 의 끝난 묶음은 건너뛴다.
6. 끝나면 마지막 셀의 `unlabeled-d-results-*.zip` 을 받아 전달한다. 크면 Drive 폴더를 통째로 받는다.

한 공고가 재시도까지 실패하면 `script.py` 는 실행을 멈춘다. 노트북은 그 공고를 `failed.json`(실패 집합 F)에
적고 빼고 다시 돈다. 설계의 중단선은 F 가 1%(20건)를 넘으면 원인부터 본다는 것이다.

## 받은 뒤 (PC)

D 는 재생 없이 각 묶음의 `submission.csv` 에서 바로 계산한다. 후보는 운영 `postprocess` 가 낸 v3·v17 셀의
근거문구만 읽으므로, CSV 의 `e3`·`e17` 에 `v3_deletion`·`v17_deletion` 을 건 결과가 후보 재생과 같다.
dev 10회차에서 두 방식의 삭제 셀이 전부 같았다. 재생은 `sme` 단계 문서 예산이 축소된 공고가 있으면
거부되므로(`replay_run.replay`) 무라벨에서는 이쪽이 필요하다.

그 뒤 D 에서 v3 19건 · v17 32건을 추첨해 라벨링한다(7절 민감도 보정 D).
D 가 그보다 작으면 같은 순서로 6,000건까지 늘린다 — 노트북 `N_NOTICES` 만 바꾸고 같은 Drive 폴더로 돌리면
끝난 묶음은 건너뛴다.
