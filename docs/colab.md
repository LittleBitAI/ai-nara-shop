# Colab에서 제출 코드 검증

현재 상태: `1c64604`는 사용자 Colab A100 40GB에서 샘플 10건·dev 200건 실제 성공,
dev Macro F1 0.2208013652894021을 확인했다. 이후 전체 프롬프트에 법령을 넣은 `9363f21`은
실행은 성공했지만 F1이 0.18470988076251235로 하락했다. 이 방식을 철회하고 현재 후보는
기존 24항목 판정 뒤 v10·v11·v13만 별도 호출한다. **새 후보의 실제 GPU·점수 개선은 미확인이다.**
목적은 서버에 다시 제출하기 전에 모델 호출·응답 형식·생성 길이 오류를 상세 로그로 확인하는 것이다.
서버와 같은 코드·모델·기본 설정·진입점을 검사하고, 통과한 ZIP을 그대로 내려받아 제출하도록 한다.
다만 Colab 성공만으로 비공개 평가 입력 전체·다른 GPU/메모리·서버 시간 제한까지 보장할 수는 없다.
이번 변경의 독립 리뷰는 사용자 지시로 생략한다.

## 준비할 파일

기본 실행은 **Colab에서 git clone**으로 준비한다. 노트북만 열면 코드·공개 입력을 가져와
기존 `tools/package.py`로 제출 ZIP/검증 번들을 자동 생성하므로 로컬 ZIP 업로드가 필요 없다.
첫 셀의 `REPO_REF="main"`은 실제 받은 커밋 SHA를 `source.json`에 기록한다.
이전 실행을 재현하려면 그 SHA를 `REPO_REF`에 지정한다. 실행 중 자동 pull은 하지 않는다.

아래 파일 업로드는 이미 생성한 특정 로컬 ZIP을 검증할 때만 사용하는 대안이다.
그때는 첫 셀의 `SOURCE_MODE="upload"`로 바꾼다.

- [Colab 노트북](../notebooks/colab-baseline.ipynb)
- `artifacts/baseline-diagnostics/colab-bundle.zip`: Colab에 업로드할 검증 자료
- `artifacts/baseline-diagnostics/submit.zip`: 번들 안에도 같은 바이트로 들어 있는 제출 후보

두 ZIP을 새로 만들려면 저장소 루트에서 실행한다. 기존 파일은 덮어쓰지 않으므로 재생성할 때는 새 경로를 사용한다.

```powershell
python -X utf8 tools/package.py --output artifacts/baseline-diagnostics/submit.zip --colab-output artifacts/baseline-diagnostics/colab-bundle.zip
```

Colab 번들은 제출 ZIP·공개 샘플 10건·dev 200건·정답 CSV·항목표·스키마·T2 채점기와
판로지원법·시행령 원본 txt 및 경쟁제품 세부품명 CSV를 포함한다.
모델·비밀키·위키·train 전체는 포함하지 않는다. 파일별 SHA-256을 업로드 후 확인한다.
clone/업로드로 준비한 뒤에는 노트북에 추론 코드를 복제하거나 다른 코드로 바꾸지 않고 **제출 ZIP의 script.py**를 실행한다.

## 실행 순서

1. [Colab](https://colab.research.google.com/)에서 **파일 → 노트북 업로드**로 `colab-baseline.ipynb`를 연다.
2. GPU 런타임을 선택하고 첫 셀부터 실행한다. 기본 clone 셀이 저장소·공개 데이터·검증 ZIP을 준비한다.
   수동 업로드 모드를 선택한 경우에만 `colab-bundle.zip` 하나를 선택한다.
3. GPU·드라이버·RAM·디스크를 기록한다. 30GiB VRAM/80GiB 여유 디스크는 노트북의 보수적인 사전 거름 기준이다.
   24GB 이하 GPU를 피하고 큰 GPU를 사용한다. 이 기준을 넘겨도 적재·추론 성공은 실행으로 확인한다.
4. uv로 Python **3.12.13**을 준비하고 별도 venv에 서버 명세 버전을 설치한다. uv는 Colab 준비 도구이며 제출물에 포함하지 않는다.
   제출 ZIP의 `requirements.txt`도 설치하고, 실제 Python·핵심 패키지·CUDA 빌드를 검사한 뒤 `pip freeze`를 남긴다.
   모든 venv Python 실행에 PATH·VIRTUAL_ENV를 전달한다. 다운로드 전에 자식 프로세스의 `ninja --version`을
   검사하고 실행 파일 경로·버전을 `runtime.json`에 남긴다.
5. **HF_TOKEN을 필수로 사용해** 고정 모델 리비전을 내려받는다. Colab 보안 비밀 `HF_TOKEN`과 노트북 접근 권한을 설정한다.
   비밀을 읽지 못하면 숨김 입력으로 받는다. 빈 토큰은 거부하며 다운로드에 `token=os.environ["HF_TOKEN"]`을 명시한다.
6. 샘플 10건 → dev 200건을 실제 모델로 실행한다. 양쪽 모두 인자 없는 `python script.py`이며 `PPS_*`로 경로만 지정한다.
   dev도 `data/test.jsonl.gz`로 준비한다. 실제 실행 설정·버전·입력 해시·코드·ZIP 일치를 검사하고 T2로 채점한다.
7. 실행 검사를 통과하면 `validation.json`을 만든다. 같은 실행의 `baseline_submission.csv`와 최종 CSV를 각각
   `score-baseline/`, `score/`로 채점한다. 다른 21항목·근거·ID가 같은지도 확인한다.
   `quality-comparison.json`은 같은 dev 해시 확인 후 양쪽 F1·3항목 지표와 과거 기준선 대비 차이를 남긴다.
   최종 F1이 같은 실행의 기본 F1보다 높고 과거 기준선 0.2208013652894021 이상일 때만
   `quality_pass=true`와 **실제로 검증한 submit.zip** 자동 다운로드를 허용한다. 재패키징하지 않는다.
   `colab_pass`는 실행 성공만 뜻하며 점수 개선이 없으면 로그 다운로드 셀로 결과만 수집한다.
8. 마지막 셀에서 `colab-results-*.zip`을 다운로드한다. **중간 셀이 실패했어도 마지막 셀은 따로 실행한다.**

토큰은 다운로드 자식 프로세스의 환경변수로만 전달한다. 추론 환경에서 토큰을 제거하고 명령행·결과 파일에 기록하지 않는다.

## 서버와 맞추는 검사

| 항목 | 검사 |
| --- | --- |
| 모델 | 고정 ID·리비전으로 다운로드, 실제 snapshot 로컬 경로 사용 |
| Python/라이브러리 | Python 3.12.13, vLLM 0.26.0, torch 2.11.0+cu130, transformers 5.14.1, xgrammar 0.2.3, CUDA 빌드 13.0 |
| 실행 | ZIP 내부 코드 복사 후 `python script.py`, 경로만 PPS 환경변수 사용 |
| 추론 | int8 weight-only·문맥 16,384·출력 2,048·청크 128·seed·temperature·thinking 등 실제 적용값 대조 |
| 검증 모드 | mock·debug·limit 우회 사용 시 통과 거부 |
| 파일 | 입력 gzip 해시, 실제 실행 파일과 ZIP 바이트, ZIP 전체 해시 대조 |
| 코드 출처 | clone한 커밋 SHA와 요청 ref·URL을 `source.json`에 기록 |
| 시간 | 제출 requirements 설치 600초, 각 샘플/dev 실행 7,200초 초과 시 거부 |
| 전달 | 샘플·dev·설정 검사·채점 성공 후에만 `colab_pass` 기록과 검증 ZIP 다운로드 |

기준은 [공식 서버 명세](https://www.dacon.io/competitions/official/236754/overview/evaluation)를 따른다.
Python 설치는 [uv의 버전 지정 설치](https://docs.astral.sh/uv/guides/install-python/)를 사용한다.
시간 검사는 공개 샘플/dev에 적용되며 **평가 입력 1,853건의 전체 소요 시간을 대신하지 않는다.**
GPU 종류·실제 메모리/CPU/RAM·OS·컨테이너 digest·OS 수준 네트워크 차단은 동일하게 복제하지 못했다.
특히 80GB GPU에서의 성공만으로 서버의 약 44.7GiB 메모리에 들어간다고 판단하면 안 된다.
이 차이는 `validation.json`에 남기며 서버 성공 보장으로 표시하지 않는다.

GPU 종류·가용 시간은 Colab에서 보장하지 않는다. [공식 FAQ](https://research.google.com/colaboratory/faq.html).
격리된 패키지 환경은 vLLM의 PyTorch/CUDA 빌드 호환성을 보존하기 위한 것이다.
[vLLM GPU 설치 안내](https://docs.vllm.ai/en/v0.26.0/getting_started/installation/gpu/).
드라이버나 설치 충돌이 발생하면 먼저 로그를 확보하고, 서버 고정 패키지를 임의로 낮추지 않는다.

노트북은 `snapshot_download(..., revision=고정_SHA)`를 준비 단계에서만 사용한다.
[Hugging Face 다운로드 안내](https://huggingface.co/docs/huggingface_hub/guides/download).
추론 프로세스는 로컬 snapshot 경로와 HF offline 설정을 사용한다. 이는 OS 수준 네트워크 차단 검증과는 다르다.
GPU·드라이버·OS가 서버와 다를 수 있으므로 로그의 실제 환경을 비교한다.

## 진단 파일 읽기

2026-09-17 결과 ZIP의 `FileNotFoundError: 'ninja'`는 패키지 미설치가 아니라 Colab 실행기의 PATH 누락이었다.
최신 노트북을 다시 열고 첫 셀부터 새 작업 폴더로 실행한다. 기존 실패 로그는 덮어쓰지 않는다.
같은 런타임의 Hugging Face 캐시가 남아 있으면 모델 파일은 재사용된다.
상세 증거는 [Colab 실패 기록](../reports/t1-baseline/colab-ninja-failure.md)을 따른다.

`script.py`는 실행 시작부터 `output-dir/diagnostics.jsonl`을 만들고 이벤트마다 flush한다.
이 파일이 이미 있으면 재사용을 거부한다. 실패한 실행도 새 출력 디렉터리로 다시 실행한다.

| 이벤트/파일 | 확인할 것 |
| --- | --- |
| `run_started`, `assets` | 실행 인자·적용 설정·코드/입력/항목표/스키마 해시·설치 버전 |
| `model_loading`, `model_loaded` | 모델 로드 단계, 적용 스키마/프롬프트 해시, 실제 템플릿 해시·CUDA·GPU·sampling 설정 |
| `chunk_started` | 청크 시작 위치와 건수; 위치는 0부터 시작 |
| `response` | 공고 ID·전체/청크 인덱스·시도 번호·정상/실패·오류 메시지·입력/출력 토큰·종료 사유 |
| `batch_failed`, `retry_failed` | 호출/응답 건수/파싱 중 어느 단계가 실패했는지, 원인 예외 |
| `retry_strategy=split_items`, `groups` | 실패 공고의 6항목씩 분할 재시도, 각 그룹의 항목·상태·생성 토큰·종료 사유 |
| `run_failed` | 원인 예외 체인을 포함한 전체 Python traceback |
| `run_succeeded`, `run_report.json` | 전건 검증·실제 모델 성공 건수·소요 시간·재현 정보 |
| Colab `*.log`, `*-command.json` | 자식 프로세스 stdout/stderr 전체, 실행 명령·종료 코드·총시간 |

`finish_reason`, `stop_reason`, 생성 토큰은 vLLM 응답에서 가져온다.
[vLLM CompletionOutput 문서](https://docs.vllm.ai/en/v0.26.0/api/vllm/outputs/).
호출 자체가 실패한 경우 생성 정보가 없는 것이 정상이다. 앞선 호출 값을 재사용하지 않는다.
`finish_reason=length`와 출력 토큰 수를 확인해야 출력 상한 도달 여부를 판별할 수 있다.
근거가 없는 상태에서 토큰 예산이나 재시도 횟수를 변경하지 않는다.

현재 후보는 같은 24항목 출력을 반복하는 대신 실패 공고만 6항목씩 4회 요청한다.
재시도 근거는 스키마로 100자 이하로 제한하고 입력+출력 토큰 예산을 다시 확인한다.
정상 응답은 재호출하지 않으며, 네 그룹 모두 검증한 경우만 합쳐서 성공으로 처리한다.
이것은 재현한 잘림 경로의 복구 보완이며, 최초 서버 오류의 실제 원인을 확정한 것은 아니다.

별도 3항목 판정은 같은 모델 인스턴스를 재사용한다. 해당 호출이 실패하면 항목 하나씩 재요청하고
3항목 전체를 검증해야 합친다. 두 단계 모두 성공한 후 기본 CSV·최종 CSV·보고서를 게시한다.
진단의 `phase=baseline/sme`, 보고서의 `baseline_inference_seconds`, `sme_inference_seconds`,
`sme_model_success_count`로 단계별 실행을 구분한다. 새 호출에 이전 예측이나 다른 공고 정보는 넣지 않는다.

현재 후보는 기본·별도 판정·재시도 지시를 영어로 작성하고 법적 용어·법령·공고 원문은 한국어로 유지한다.
`baseline_submission.csv`는 이번 영어 지시의 24항목 첫 판정이며 과거 한국어 기준선 재실행본은 아니다.
별도 단계는 3항목의 품목 코드·대상 인용·자격 문구·적용/예외 상태를 먼저 추출한다.
코드는 실제 조회 후보와 원문 인용을 대조하고 v13의 중기업 포함 문구와 미관측 부재 단정을 거른다.
`sme_verified` 이벤트와 `sme_verified_count`, `sme_rejected_positive_count`를 함께 확인한다.
형식이 깨진 사실 응답은 분할 복구하며, 복구 실패를 0 판정으로 대체하지 않는다.
품질 기준은 여전히 같은 실행의 기본 F1 초과 및 과거 F1 0.2208013652894021 이상이다.

기본 제출 실행에는 공고 본문·원응답을 별도 기록하지 않는다. 원인 예외 메시지와 traceback은 보존한다.
공개 dev의 원응답이 필요하면 별도 진단 실행에 `--debug-responses`를 사용한다.
현재 Colab 통과 검사는 대회 기본 명령과 같게 실행하므로 이 옵션을 켜지 않으며, 켜진 결과를 검증 통과로 인정하지 않는다.
원응답은 `response_text`에 들어가며 로그를 외부 공유하기 전에 내용을 확인한다.

샘플/dev가 통과해도 서버에서 실패한 비공개 공고가 재현된 것은 아니다.
결과 ZIP을 분석한 후 수정이 필요하면 코드 변경 → 새 제출/Colab 번들 생성 → 같은 검증을 반복한다.
검증 뒤 소스가 바뀌면 이전 ZIP의 성공을 새 코드의 검증으로 사용하지 않는다.
