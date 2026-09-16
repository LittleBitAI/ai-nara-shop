# 대회 고정 Gemma 4: 모델 특성과 실행·프롬프트 결정

조사일: 2026-09-16. 대상은 `google/gemma-4-26B-A4B-it`,
리비전 `4d7ae4984b7db7de8f8457170b3f1a419ee76d52`이다.
공식 기술 보고서·고정 리비전 파일·공식 런타임 문서를 우선했다.
아래 **사실**은 출처에서 확인한 내용, **적용 판단**은 이번 과제에 대한 설계,
**실험 후보**는 아직 효과를 검증하지 않은 제안이다. 법령 지식은 제공 스냅샷만 사용한다.
이 문서는 개발 참고 자료이며 검색 인덱스나 제출 ZIP에 넣지 않는다.

## 어떤 모델인가

Gemma 4는 Google DeepMind의 공개 가중치 decoder-only 모델 계열이다.
이 대회의 IT 모델은 지시 수행용이며, 26B-A4B는 MoE 변형이다.
공식 기술 보고서 §2·표 1은 총 약 26B와 활성 3.8B를 구분한다.
§2는 local/global attention 5:1 및 global layer의 key/value 재사용·p-RoPE를 설명한다.
§2.4의 토크나이저는 숫자 분리·공백 보존·byte 표현을 사용한다.
따라서 1글자=1토큰으로 예산을 보장할 수 없다.
§2.4의 사전학습 cutoff는 2025년 1월이다.
§3은 thinking과 문맥 내 출처 귀속을 포함한 지시 튜닝을 설명한다.
법령 스냅샷·예외를 모델 기억만으로 대신할 근거는 없다.
[Gemma Team, *Gemma 4 Technical Report*, 2026-07-02, §2–3](https://arxiv.org/html/2607.02770v1)

위 논문은 **개발팀의 arXiv 기술 보고서**이며 동료심사 학술지 게재 논문으로 확인한 것은 아니다.
모델 고유 구조의 일차 자료로 쓰고, 일반 기법은 아래 동료심사 논문과 구분한다.

| 고정 리비전 모델 카드의 항목 | 확인한 값 | 적용 판단 |
| --- | --- | --- |
| MoE | 128 expert 중 8개 활성 + shared expert 1개 | 전체 가중치 메모리와 토큰당 계산량을 구분 |
| 층·local window | 30층·1,024 토큰 | local window를 전체 문맥 상한으로 오해하지 않음 |
| 문맥 지원 | 256K 토큰 | 대회 서버의 더 작은 상한과 시간 제한이 우선 |
| 입력 모달리티 | 텍스트·이미지 | 제공 텍스트만 사용하며 외부 OCR/이미지 취득 없음 |
| 역할 | system/user/assistant 지원 | Gemma 3용 system 역할 우회 코드를 가져오지 않음 |

모델 카드의 25.2B 표기와 기술 보고서의 약 26B 표기는 집계·반올림 범위가 다르다.
어느 표기도 “가중치 전체가 4B”라는 뜻은 아니다.
[고정 리비전 모델 카드: Architecture·Best Practices](https://huggingface.co/google/gemma-4-26B-A4B-it/blob/4d7ae4984b7db7de8f8457170b3f1a419ee76d52/README.md)

## 대회에서 실제로 지켜야 하는 실행 한계

대회 서버는 L40S 1장, 가용 VRAM 약 44.7GiB이며 모델의 bf16 원본이 적재되지 않아
양자화가 필요하다. 허용 문맥 상한은 32,768, 제공 베이스라인은 16,384와
`int8_per_channel_weight_only`를 사용한다. 로드·전처리 포함 2시간 안에 끝나야 한다.
오늘은 이 실행 설정을 유지하며, 논문의 QAT 모델이나 MTP drafter를 별도 반입하지 않는다.
공식 문서에 빠른 다른 변형이 있다는 사실은 대회의 고정 리비전 교체 허가가 아니다.
[공식 평가 환경·모델 제한](https://www.dacon.io/competitions/official/236754/overview/evaluation)

## 이 모델에 특히 중요한 채팅·thinking 처리

고정 리비전 `chat_template.jinja`의 SETUP은 `enable_thinking` 기본값을 false로 두고,
켜면 첫 system turn에 thinking 토큰을 넣는다. 생성 프롬프트에서 끄면 빈 thought 채널을
자동으로 붙인다. 따라서 문자열로 특수 토큰을 수동 조립하거나 빈 채널을 중복 추가하지 않는다.
서버가 로드한 tokenizer의 템플릿을 사용하고, `enable_thinking=False`를 토큰 계산과
`LLM.chat(chat_template_kwargs=...)` 양쪽에 동일하게 전달한다.
[대회 리비전의 실제 템플릿](https://huggingface.co/google/gemma-4-26B-A4B-it/blob/4d7ae4984b7db7de8f8457170b3f1a419ee76d52/chat_template.jinja)

Google은 thinking을 꺼도 큰 모델에 thought 채널이 나타날 수 있음을 명시한다.
반환된 thought를 JSON 판정이나 근거문구로 사용하지 않는다. 최종 답변만 파싱하며,
닫히지 않은 thought·불완전 JSON은 정상 결과가 아니다. 일반 대화 이력에 이전 thought를
그대로 재투입하지 않는 것이 공식 규약이며, 이 과제는 아예 공고별 새 대화를 만든다.
[공식 Prompt Formatting: Thinking·Integration Notes](https://ai.google.dev/gemma/docs/core/prompt-formatting-gemma4)

오늘의 판단: thinking off + JSON Schema 제약 디코딩 + 짧은 근거로 실행 기준선을 만든다.
이것은 속도·완결성을 위한 선택이며 thinking off의 정확도 우위를 입증한 결과가 아니다.
단순히 “단계별로 길게 생각하라”를 넣는 것은 모델 고유 thinking 제어와 다르다.

## 프롬프트와 생성 설정

고정 리비전 `generation_config.json`은 sampling 활성, temperature 1.0, top-p 0.95,
top-k 64를 제공한다. 반면 대회 베이스라인은 temperature 0의 결정적 출력을 택한다.
둘 중 어느 쪽이 이 법령 다중 판정에 우수한지는 미측정이다. 오늘은 베이스라인의 0을 유지하고,
공식 sampling 조합은 별도 동일-dev 실험으로 비교한다. 공식 권고를 읽었다는 이유만으로
점수 개선이 검증된 것처럼 바꾸지 않는다.
[고정 리비전 생성 설정](https://huggingface.co/google/gemma-4-26B-A4B-it/raw/4d7ae4984b7db7de8f8457170b3f1a419ee76d52/generation_config.json)

이번 과제에 대한 프롬프트 적용 판단:

- system에는 역할·24항목 이름·출력 규약을, user에는 현재 공고의 메타·관측성·문서를 둔다.
- 적용계약법·대상·금액 기준·예외를 확인하도록 지시한다. 숫자나 법적 임계값을 조사 모델의 기억으로 추가하지 않는다.
- 근거는 현재 공고 문서의 짧은 연속 인용만 허용한다. v=0·부재탐지는 null, CSV에서는 빈칸이다.
- null과 미입력, 해당 없음을 구분한다. 문서 절단/누락을 부재 사실로 확정하지 않는다.
- v24는 메타와 문서를 직접 대조한다. 법령 텍스트를 근거 e로 출력하지 않는다.
- JSON 키를 정확히 제한한다. 모델이 낸 bool·확률·문자열을 임의로 0/1로 바꾸지 않는다.

이는 입력·출력 계약을 분명히 하는 설계이며, 어떤 문구가 F1을 높이는지는 dev와 서버 결과로 판정한다.

## 논문에서 얻은 근거와 한계

| 논문 | 확인한 결과·범위 | 이 과제에서의 사용 |
| --- | --- | --- |
| [Gemma 4 Technical Report, 표 5](https://arxiv.org/html/2607.02770v1#S4) | 26B-A4B의 IFEval 98.5, MRCR v2 8-needle 128K 44.1. 표는 별도 표시 외 thinking 모드 | 지시 이행 벤치마크와 긴 문맥 검색은 별개다. 한국 법령 F1·양자화 서버·thinking off 성능으로 환산하지 않는다 |
| [Dong et al., XGrammar, MLSys 2025](https://proceedings.mlsys.org/paper_files/paper/2025/hash/5c20ca4b0b20b0bd2f1d839dc605e70f-Abstract-Conference.html) | 문법 기반 토큰 제약·캐싱·추론과 겹친 실행으로 구조화 생성 비용을 줄임 | JSON 구조 보장에 제약 디코딩 사용. 의미·법령 정오·원문 인용은 별도 검증. 논문 속도 수치를 L40S 실측치로 사용하지 않음 |
| [Liu et al., Lost in the Middle, TACL 2024, pp.157–173](https://aclanthology.org/2024.tacl-1.9/) | 평가 모델에서 관련 정보 위치에 따라 긴 문맥 활용 성능 변화 관측 | Gemma 4 직접 실험이 아니다. 전체 문맥을 채우기보다 문서 선택·배치 순서를 시험할 일반 가설로만 사용 |

## 첫 제출 뒤 한 번에 하나씩 비교할 실험

1. **문서 손실:** 4K/16K 글자 시작 예산을 같은 실제 토크나이저 예산으로 조정해 비교한다.
   항목별 FN, 첨부 포함률, 근거 폐기율, 총시간을 기록한다. 글자 수 증가는 효과 보장이 아니다.
2. **근거 주입:** 공식 항목표→제공 조문 직접 조회와 노트북 BM25를 각각 비교한다.
   질의가 공고 도입부 3K에만 치우치는지 확인하고, 검색 조문 때문에 공고가 밀려나지 않게 한다.
3. **생성 방식:** temperature 0 vs 공식 sampling 조합을 고정 seed로 비교한다.
   무작위 후보는 여러 seed의 변동도 확인한다. 한 번의 우연한 상승으로 채택하지 않는다.
4. **thinking:** off 기준선이 확보된 뒤, 같은 공고 입력의 on 후보를 별도 검증한다.
   reasoning과 최종 JSON 분리·제약 디코딩 호환·출력 완결·총시간까지 통과해야 한다.

오늘 제외: 외부 가중치/QAT/MTP 모델 교체, 학습·LoRA, 최신 법령 수집, 공고 간 대화 공유,
미측정 self-consistency 다중 호출. 이유는 각각 대회 제한 또는 첫 제출의 시간·검증 비용이다.

## 구현 확인표

- 고정 서버 경로로만 모델 로드. 네트워크 다운로드 없음.
- tokenizer 템플릿과 추론 템플릿의 thinking 설정 동일.
- 입력 토큰 + 출력 예약 + 여유가 16,384 이하. 템플릿 실패 시 근사 계산으로 통과시키지 않음.
- 모델 정상 응답·24항목 검증 실패를 성공 CSV로 바꾸지 않음.
- 구조화 출력은 [vLLM 0.26.0의 offline chat API](https://docs.vllm.ai/en/v0.26.0/api/vllm/entrypoints/llm/)로 실행.
- 서버의 실제 tokenizer 템플릿 hash·패키지 버전을 실행 기록으로 남겨 리비전 차이를 추적.

## 로컬 토크나이저 검사

고정 리비전의 tokenizer.json·tokenizer_config.json·chat_template.jinja만 받아 검사했다.
가중치는 다운로드하지 않았다. 로컬 transformers 4.57.6의 범용 PreTrainedTokenizerFast와
tokenizers 0.22.2로 고정 토크나이저·템플릿을 적용했다. 이는 서버의 transformers 5.14.1
GemmaTokenizer나 vLLM과 동일한 런타임 검사는 아니다.

dev 200건의 후보 입력 토큰은 최소 3,307·중앙값 9,494·최대 12,280이었다.
모두 출력 예약 2,048 및 여유 64를 포함해 16,384 이내였고, 전부 0 JSON은 424토큰이었다.
생성 프롬프트 끝에 빈 thought 채널이 정확히 들어가는 것도 확인했다.
파일 SHA-256·환경·한계는 [검사 기록](../reports/t1-baseline/tokenizer-check.json)에 남겼다.
서버 모델은 아직 호출하지 않았다. 대회 점수·처리속도 개선은 아직 입증하지 않았다.
