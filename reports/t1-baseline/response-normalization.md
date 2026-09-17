# 성공 제출본 대조와 응답 정규화

## 비교 증거

사용자가 제공한 팀원 성공 제출본 script.py는 open/baseline/script.py와 바이트 단위로 같다.
SHA-256: `3f410ee6f7c24da25ba25e9bef2501b7715222cfb047363fbe8ab5b57fd17fbb`.
최초 실패 ZIP의 script.py SHA-256은 `9abb9c4e53880a40701f14c724d1dfeff3604cea3f5e52ebfb593cdf993db5b7`.
팀원/최초 실패본의 requirements.txt는 같다. 팀원 실제 응답이나 0 채움 발생 여부는 알 수 없다.

같은 잘린 JSON을 청크 62에 주입한 로컬 비교에서 팀원 코드는 해당 공고의 24항목을
0으로 채워 128행 CSV 형식 검사를 통과했다. 최초 실패본은 사용자와 동일한
`청크 내 62번 공고: 정상 모델 응답 재시도 실패 (ValueError)`로 종료하고 CSV가 없었다.
빈 응답·필드 누락·bool/문자열/float 이진값·추가 필드에서도 종료 정책 차이를 재현했다.
최초 서버 응답이 이 중 무엇이었는지는 미확정이다.

입력 상한은 팀원 4,000자, 최초 실패본 16,000자다. 보관 고정 모델 토크나이저로 dev 200건을
계산하면 입력 중앙값/최대가 각각 3,850/4,205 및 9,493/12,279토큰이었다.
짧은 입력의 이점만 보고 공고 정보를 줄이지 않는다. 문서·프롬프트·출력 예산은 유지한다.

## 변경

- JSON의 true/false, 숫자 0/1 및 0.0/1.0, 문자열 0/1/true/false를 정수 0/1로 정규화한다.
  문자열 앞뒤 공백·대소문자 차이는 허용한다. 그 외 값의 참/거짓 여부로 위반을 추측하지 않는다.
- 최상위·항목·facts의 추가 설명 필드는 무시한다. 필수 키는 모두 있어야 한다.
  facts의 코드·enum·인용 타입/길이 등 기존 검증은 유지한다.
- 0.5, 2, -1, unknown, 빈 문자열, 리스트/객체/null, 항목 누락, 깨진/빈 응답은
  정상 판정으로 바꾸지 않는다. 기존 24→6→1 복구 및 추가 실패 시 검증된 기본 응답 보존을 사용한다.
- 정상 호출 없는 공고를 0으로 채우는 팀원 동작은 도입하지 않는다.
  제출 스키마·CSV는 기존 정수 0/1 계약을 유지한다. 완화는 의미가 명확한 응답 표현에 한정한다.
- 모델 지시는 영어, 법적 용어는 한국어로 유지한다. 기존 점수 임계값·위반 판단 조건은 유지한다.
  서버 로그 열람을 전제로 하지 않으며 새 로그 기능은 추가하지 않았다.

## 검증

수정 전 `test_equivalent_responses_do_not_retry_chunk_62`는 기본/추가 단계 16개 조합에서
불필요한 재시도로 실패했다. 수정 후 재호출 없이 성공하고 최종 내부 판정은 정수 0/1이다.

- `python -X utf8 tests/test_baseline.py`: 17개 통과, 4.446초.
- `python -X utf8 tests/test_package.py`: 5개 통과, 24.876초.
- `python -X utf8 tests/test_score.py`: 4개 통과, 12.078초.
- Ruff·diff 검사 통과. dev 200건 기본/추가 프롬프트 동일성 및 정상 JSON의 파싱 결과 동일성 확인.
- `python -X utf8 tools/package.py --output artifacts/response-normalization/submit.zip
  --colab-output artifacts/response-normalization/colab-bundle.zip`: 압축 해제 mock 10건·49열,
  모델 없는 기본 진입 실패 검사 통과.

후보 ZIP SHA-256: `9d60e30e43ac10ee4c982e411d99b537e99467f7e22ee374b938a147af8c08b0`.
script.py SHA-256: `79a56041153d6a125bd12d9f59780ee092fe48e9a2837fb5e38c50c821d5c04c`.

검증은 모델 없는 로컬 검사다. 새 후보의 실제 GPU 실행·서버 성공·점수 개선은 미검증이다.
출력 잘림·엔진 오류를 이 정규화만으로 없앴다고 주장하지 않는다. 실제 Colab은 같은 ZIP으로 검증한다.
