# T1 서버 실패 진단 (2026-09-17)

사용자 보고: `제출하신 코드 실행 중 에러가 발생했습니다 - InstallError : 청크 내 62번 공고: 정상 모델 응답 재시도 실패 (ValueError)`.
사용자는 `artifacts/baseline`의 로컬 T1 제출 ZIP을 그대로 업로드했다고 확인했다.
서버 전체 로그·제출 ID·제출 시각·모델 원응답은 제공되지 않았다.

## 확인한 실행 자산

- ZIP SHA-256: `d3d6622e5171cb368adc4f9e5618f9f20f90442a5d3dc64e362a6766c36a9b6a`.
- ZIP 내부 `script.py`: `9abb9c4e53880a40701f14c724d1dfeff3604cea3f5e52ebfb593cdf993db5b7`.
- ZIP은 제출 전 `manifest.json`의 해시와 일치하며 내부 두 파일은 현재 소스와 바이트 단위로 같다.
- `requirements.txt`는 주석만 있다. 보고된 한국어 오류는 `script.py:363`에서 생성한다.
  플랫폼의 `InstallError` 이름만으로 패키지 설치 실패라고 판단할 수 없다.
- 아래 재현은 ZIP 내부 소스를 메모리에서 불러와 실행했다. 서버 모델 실행 재현은 아니다.
  로컬에는 vLLM이 설치되어 있지 않으며 유료 GPU·서버 제출을 실행하지 않았다.

## 확인한 실패 경로

`run()` → `run_chunk()` → 배치 호출 또는 응답 검증 실패 → 해당 공고 단독 재시도 →
호출/응답 건수/판정 검증 중 `ValueError` → `RuntimeError`로 감싸기 → `main()`이 한 줄만 출력하고 종료 코드 1 반환.

- 62는 `enumerate(batch)`의 0부터 시작하는 인덱스다. 해당 청크의 **63번째** 공고이며 실제 공고 ID가 아니다.
  기본 청크 크기는 128이다. 어느 청크인지 없으므로 전체 입력의 63번째 공고로 단정할 수 없다.
- 같은 청크에서 앞선 62개 응답은 검증을 통과한 상태다. 최초 호출 또는 재시도 중 어느 쪽으로 통과했는지는 알 수 없다.
- 마지막 `ValueError`는 `runner.chat([m])`, 재시도 응답 건수 검사, `parse_judgment()` 중 어디서든 발생할 수 있다.
  따라서 이 문구만으로 “두 번 모두 JSON이 잘렸다”거나 “모델 호출 자체는 성공했다”고 확정할 수 없다.
- `raise ... from e`에는 원인 예외가 연결되지만 `main()`이 traceback을 출력하지 않는다.
  최종 문구는 `type(e).__name__`만 담아 원인 메시지가 사용자에게 전달되지 않는다.
- `VLLMRunner.chat()`은 응답의 `.text`만 반환한다. 종료 사유·생성 토큰 수는 보존하지 않는다.
  성공 보고서·CSV 작성은 전건 추론 뒤에 있으므로 이 실패 경로에서는 생성되지 않는다.

## 동일 문구 재현

최초 배치의 인덱스 62에 빈 응답을 주고 다른 127개에는 정상 24항목 JSON을 주었다.
단독 재시도에 아래 값을 각각 주입하면 모두 보고된 한국어 문구와 정확히 일치했다.
호출 크기도 각각 `[128, 1]`이었다.

| 주입한 재시도 결과 | 원인 예외의 실제 메시지 |
| --- | --- |
| 끝의 두 문자를 자른 JSON | 정상 24항목 JSON이 아니다 |
| 빈 문자열 | 정상 24항목 JSON이 아니다 |
| 위반여부 `1.0` | v1: 위반여부는 정수 0 또는 1이어야 한다 |
| 호출 자체가 ValueError 발생 | simulated runtime ValueError |
| 응답 목록 `[]` | 재시도 응답 건수 불일치 |

가장 작은 재현 명령은 저장소 루트에서 다음 Python을 실행하는 것이다.
모델을 호출하지 않고 오류 전달 경로만 검사한다.

```python
import json
import types
import zipfile

module = types.ModuleType("submitted_baseline")
with zipfile.ZipFile("artifacts/baseline/submit.zip") as archive:
    exec(compile(archive.read("script.py"), "submitted/script.py", "exec"), module.__dict__)
good = json.dumps({v: {"위반여부": 0, "근거문구": None} for v in module.ITEMS})

class Runner:
    def chat(self, batch):
        return [good] * 62 + [""] if len(batch) > 1 else [good[:-2]]

try:
    module.run_chunk(Runner(), [[] for _ in range(63)])
except RuntimeError as error:
    assert str(error) == "청크 내 62번 공고: 정상 모델 응답 재시도 실패 (ValueError)"
    assert str(error.__cause__) == "정상 24항목 JSON이 아니다"
    print(error)
    print("숨겨진 원인:", error.__cause__)
else:
    raise AssertionError("실패 경로가 재현되지 않음")
```

## 출력 길이 가설의 근거와 한계

코드는 `max_tokens=2048`, `temperature=0.0`, 고정 seed를 사용한다.
재시도에서도 같은 메시지와 같은 SamplingParams를 사용한다.
출력 상한 부족처럼 반복되는 조건은 재시도에서도 그대로다. 실제 출력의 바이트 동일성은 측정하지 않았다.

근거문구는 항목당 500자까지 허용되므로 스키마가 허용한 JSON 전체가 2,048토큰 이내라는 보장은 없다.
보관된 고정 리비전 `tokenizer.json`의 SHA-256을 기존 검사 기록과 대조한 뒤,
`tokenizers.Tokenizer.encode(..., add_special_tokens=False)`로 압축 JSON 길이를 측정했다.
제공 dev 첫 공고의 첫 문서 앞부분을 비부재탐지 19개 항목에 동일하게 넣은 **합성 출력**이다.
법령 정답·실제 모델 응답이 아니며 `jsonschema.validate`로 구조 적합성만 확인했다.

| 합성 출력 | 토큰 수 |
| --- | --- |
| 전부 0, 근거 null | 424 |
| 각 근거 100자 | 1,867 |
| 각 근거 500자 | 7,738 |

반대로 제공 dev 정답 200건을 같은 JSON 형식으로 직렬화했을 때는 424~640토큰으로,
2,048을 넘는 건이 없었다. **현재 증거는 잘림 가능성을 보여 줄 뿐, 이번 실패나 일반적인 예산 부족을 증명하지 않는다.**
문자열 잘림·빈 출력·필드/타입 오류·런타임 오류 중 실제 원인을 고르려면 서버 증거가 필요하다.

## 다음 확인

1. 기존 서버 로그에 원인 예외·생성 종료 사유가 있으면 먼저 확인한다.
2. 기존 로그가 없다면 후속 수정에서 실패 단계, 원인 예외 메시지, 청크 위치,
   `finish_reason`·`stop_reason`·생성 토큰 수·출력 상한·파싱 오류 종류를 보존한다.
   비공개 공고 본문·모델 인용 내용을 외부 로그로 유출하는 방식은 사용하지 않는다.
3. 길이 제한 종료가 확인되면 출력 예약/근거 길이를 조정하고 입력+출력 예산 및 총 실행 시간을 함께 검증한다.
   호출 오류나 스키마/파서 문제이면 해당 경로를 수정한다. 재시도 횟수 증가만으로 원인을 해결했다고 보지 않는다.

이번에는 제출 코드·ZIP을 변경하지 않았다. 유효 제출·실제 모델 성공을 확인하지 않았으며 T1은 진행 중이다.
기존 `manifest.json`의 `server_submitted: false`는 제출 전 검사 시점 기록으로 보존한다.
