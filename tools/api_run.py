"""대회 고정 모델과 같은 Gemma 4를 Google AI Studio API로 불러 dev 파이프라인을 그대로 돌린다.

키가 있으면 실제 모델로, 없으면 mock으로 떨어진다. 팀원이 키가 없어도 같은 명령이 돈다.
제출 코드에는 네트워크 코드를 넣지 않는다 — `script.py`를 모듈로 불러 `run()`에 러너만 갈아 끼운다.
Colab 왕복 없이 프롬프트·스키마 후보의 표본을 쌓는 용도다.

  python -X utf8 tools/api_run.py --output-dir runs/api-001 --limit 10
  python -X utf8 tools/api_run.py --output-dir runs/api-dev --debug-responses

`runs/`는 gitignore된 로컬 폴더다. 여기 쌓인 원응답은 **내 기계에만 있다** — Colab 회차가
`reports/runs/<run-id>/`에 추적되는 것과 다르다. 팀이 이 corpus를 쓰려면 보관 규약
(docs/runs.md)에 API 회차를 어떻게 넣을지 정해야 한다. `tools/register_run.py`는
Colab 결과 ZIP 한 쌍을 받으므로 그대로는 안 맞는다.

규칙 판단: 단계 = 개발·로컬 검증 / 활용 A3·A9 / 지킬 R6·R7·R9·R11·R15.
- 부르는 모델은 R1 고정 모델과 같은 `gemma-4-26b-a4b-it`이지만 **같은 실행이 아니다.**
  Google 호스팅은 고정 리비전·int8 양자화·고정 chat_template을 보장하지 않고,
  이 모델은 API에서 `thinkingConfig`를 받지 않아 `enable_thinking=False`도 못 건다.
  그래서 mode는 `live`가 아니라 `api`이고 `model_success_count`는 0으로 남는다.
  **R4 정상 호출 증거도, 서버 점수의 대체도 아니다.**
- R7 제출 추론은 이 경로를 쓰지 않는다. 이 파일은 제출 ZIP allowlist(`tools/package.py`의
  `FILES`) 밖이고, `script.py`는 이 모듈을 import하지 않는다.
- R9 입력은 공개 dev와 제공 무라벨뿐이다. 비공개 평가 데이터에 쓰지 않는다.
- R11 법령은 제공 스냅샷 그대로 프롬프트에 들어간다. 웹 검색·외부 문서 결합이 없다.
- R15 모델 이름·응답 ID·프롬프트 hash·설정을 `api-run.json`과 diagnostics에 남긴다.
- Q1: 이것은 "우리 프롬프트에 모델이 어떻게 답하나"를 보는 로컬 검증이다. API가 만든 라벨을
  자산으로 채택하는 것은 별개 판단이며 Q1 확인 전까지 보류다.
- 키는 환경변수·`.env`로만 받고 인자·기록·로그에 넣지 않는다(W6). `run()`의 `settings`는
  그대로 run_report.json에 실리므로 키를 생성자 인자로 넘기지 않는다.
"""

import argparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import random
import re
import sys
import threading
import time
from types import SimpleNamespace
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HOST = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemma-4-26b-a4b-it"
KEY_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
RETRY_CODES = frozenset({408, 429, 500, 502, 503, 504})
RETRY_HINT = re.compile(r"retry in ([\d.]+)s")
# 429 본문이 지금 걸린 상한을 그대로 적어 준다. 입력 토큰 할당량일 때만 읽는다 —
# 다른 할당량(요청 수 등)의 숫자를 토큰 예산으로 삼으면 분당 한 건으로 주저앉는다.
QUOTA_LIMIT = re.compile(r"input_token_count, limit: (\d+)")
# 이 모델의 429는 요청 수가 아니라 **분당 입력 토큰**으로 난다. 2026-09-18 실측 오류 본문:
# GenerateContentPaidTierInputTokensPerModelPerMinute-PaidTier2, limit 16000, model gemma-4-26b.
# 공고 한 건이 약 11,000 토큰이라 분당 1~2건이 상한이다. 공식 요금제 표에 Gemma 행이 없으므로
# 이 값은 시작 추정치일 뿐이고, 429를 만나면 본문이 알려 주는 실제 상한으로 갈아탄다.
DEFAULT_TPM = 16000
TOKENS_PER_NOTICE = 11000  # dev 실측 중앙값(--max-chars 16000). 시간 예상에만 쓴다.


def load_submission_script(path=None):
    """제출물 `script.py`를 그대로 불러온다. 사본을 만들지 않는다."""
    path = Path(path) if path else ROOT / "script.py"
    if not path.is_file():
        raise ValueError(f"제출 코드를 찾지 못했다: {path}")
    spec = importlib.util.spec_from_file_location("submission_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_api_key():
    """환경변수를 먼저 보고 없으면 저장소 루트 `.env`를 본다. 값은 돌려주되 기록하지 않는다."""
    for name in KEY_NAMES:
        if os.environ.get(name, "").strip():
            return os.environ[name].strip(), name
    env = ROOT / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() in KEY_NAMES and value.strip():
                return value.strip().strip("'\""), f"{name.strip()} (.env)"
    return None, None


class TokenBucket:
    """분당 입력 토큰 상한을 지킨다. 429를 맞고 41초씩 버리는 대신 미리 기다린다."""

    def __init__(self, per_minute, window=60.0):
        self.per_minute = per_minute
        self.window = window
        self.spent = deque()
        self.lock = threading.Lock()

    def take(self, tokens):
        while True:
            with self.lock:
                now = time.time()
                while self.spent and now - self.spent[0][0] >= self.window:
                    self.spent.popleft()
                # 한 건이 상한보다 크면 비었을 때 그냥 보낸다. 안 그러면 영원히 못 나간다.
                if not self.spent or sum(t for _, t in self.spent) + tokens <= self.per_minute:
                    self.spent.append((now, tokens))
                    return
                wait = self.window - (now - self.spent[0][0])
            time.sleep(max(0.05, min(self.window, wait)))


def prompt_key(messages):
    """같은 프롬프트의 토큰 수를 두 번 세지 않는다. count_tokens가 센 것을 페이서가 쓴다."""
    return hashlib.sha256("\x00".join(m["content"] for m in messages).encode("utf-8")).hexdigest()


def to_request(messages):
    """`script.py`의 chat 메시지를 generateContent 요청 본문으로 옮긴다."""
    system = [m["content"] for m in messages if m["role"] == "system"]
    body = {"contents": [{"role": "model" if m["role"] == "assistant" else "user",
                          "parts": [{"text": m["content"]}]}
                         for m in messages if m["role"] != "system"]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": "\n\n".join(system)}]}
    return body


class APIRunner:
    """고정 모델과 같은 Gemma 4를 Google AI Studio API로 부른다. 평가 서버 실행이 아니다."""

    MODE = "api"
    TOKEN_COUNT = "api_count"
    # main()이 채운다. `run()`의 runner_kw로 넘기면 키와 모듈 객체가 run_report.json에 실린다.
    KEY = None
    SCRIPT = None
    INSTANCE = None
    MODEL = DEFAULT_MODEL
    WORKERS = 4
    TIMEOUT = 300
    RETRIES = 4
    TPM = DEFAULT_TPM

    def __init__(self, schema, *, max_tokens=2048, **_):
        if not self.KEY:
            raise ValueError(f"API 키가 없다. {' 또는 '.join(KEY_NAMES)}를 환경변수나 .env에 둔다")
        # VLLMRunner의 `sp`와 같은 모양으로 둔다. 복구 전략을 그대로 빌려 쓰기 위해서다.
        self.sp = SimpleNamespace(max_tokens=max_tokens,
                                  structured_outputs=SimpleNamespace(json=schema))
        self.last_response_info = []
        self.load_seconds = 0.0
        self._lock = threading.Lock()
        self._counted = {}
        self.bucket = TokenBucket(self.TPM)
        self.calls = 0
        self.tokens = {"prompt": 0, "output": 0}
        self.environment = {
            "runner": "google_ai_studio_api", "api_model": self.MODEL,
            "endpoint": f"{HOST}/models/{self.MODEL}", "python": platform.python_version(),
            "structured_output": "responseJsonSchema", "temperature": 0, "workers": self.WORKERS,
            "input_tokens_per_minute": self.TPM,
            "thinking": "미제어 — 이 모델은 API에서 thinkingConfig를 받지 않는다",
            "note": "고정 리비전·양자화·chat_template이 평가 서버와 같다는 보장이 없다",
        }
        type(self).INSTANCE = self  # run()은 러너를 안 돌려준다. 호출 수를 읽는 유일한 통로다.

    # ---- HTTP ----
    def _post(self, url, body):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        attempts = max(1, self.RETRIES)
        for attempt in range(1, attempts + 1):
            request = urllib.request.Request(url, data=payload, headers={
                "x-goog-api-key": self.KEY, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(request, timeout=self.TIMEOUT) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                # 본문 전체에서 찾는다. "Please retry in 41.9s"는 400자쯤 뒤에 있어서
                # 잘라낸 조각에서 찾으면 영영 안 걸리고 조용히 지수 백오프로 돌아간다.
                detail = error.read().decode("utf-8", "replace")
                self._adopt_limit(detail)
                if error.code not in RETRY_CODES or attempt == attempts:
                    raise ValueError(f"HTTP {error.code}: {detail[:300]}") from None
                hint = RETRY_HINT.search(detail)
                wait = float(hint.group(1)) + 1 if hint else None
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if attempt == attempts:
                    raise ValueError(f"{type(error).__name__}: {error}") from None
                wait = None
            # 서버가 "Please retry in 360s"라고 알려 주면 그 값은 자르지 않는다.
            # 90초로 자르면 90·180·270초에 두드려 전부 429를 맞고, 한 번만 기다렸으면
            # 성공했을 요청이 회차를 통째로 끝낸다 — count_tokens()는 이 실패를
            # 공고별 복구 없이 그대로 올린다. 상한은 힌트가 없을 때의 지수 백오프에만 건다.
            time.sleep(wait if wait else min(90.0, 2 ** attempt + random.random()))

    def _adopt_limit(self, detail):
        """공식 문서의 요금제 표에 Gemma 행이 없다. 실제 상한은 429가 알려 주는 것이 유일한 사실이라,
        `--tpm` 추정치 대신 그 값을 쓴다. 등급을 올리면 다음 회차가 알아서 빨라진다."""
        found = QUOTA_LIMIT.search(detail)
        if not found or int(found.group(1)) == self.bucket.per_minute:
            return
        print(f"  분당 입력 토큰 상한을 {self.bucket.per_minute:,} → {int(found.group(1)):,}"
              " 으로 바꾼다 (429 본문이 알려 준 값)")
        self.bucket.per_minute = int(found.group(1))

    def _record(self, usage):
        with self._lock:
            self.calls += 1
            self.tokens["prompt"] += usage.get("promptTokenCount") or 0
            self.tokens["output"] += usage.get("candidatesTokenCount") or 0

    # ---- script.py 러너 계약 ----
    def count_tokens(self, messages):
        body = {"generateContentRequest": {"model": f"models/{self.MODEL}", **to_request(messages)}}
        data = self._post(f"{HOST}/models/{self.MODEL}:countTokens", body)
        total = int(data["totalTokens"])
        self._counted[prompt_key(messages)] = total
        return total

    def _one(self, messages, sp):
        # fit_to_budget이 이미 센 값이다. 못 찾으면 글자 수로 센다 — 한국어는 글자당 1토큰이
        # 안 되므로 넉넉한 쪽으로 틀린다. 여기서 한도를 통째로 물리면 호출이 분당 한 건이 된다.
        counted = self._counted.get(prompt_key(messages))
        self.bucket.take(counted or sum(len(m["content"]) for m in messages))
        body = to_request(messages)
        body["generationConfig"] = {
            "temperature": 0, "candidateCount": 1, "maxOutputTokens": sp.max_tokens,
            "responseMimeType": "application/json",
            "responseJsonSchema": sp.structured_outputs.json,
        }
        started = time.time()
        try:
            data = self._post(f"{HOST}/models/{self.MODEL}:generateContent", body)
        except ValueError as error:
            # 한 건의 실패로 나머지 배치를 버리지 않는다. 빈 응답은 공고별 재시도로 넘어간다.
            # 키 이름에 `api_`를 붙인다. `error_type`·`error_message`는 run_chunk의 record()가
            # 자기 인자로 쓰므로 그대로 쓰면 진짜 실패가 TypeError에 가려진다.
            return "", {"api_error_type": type(error).__name__, "api_error_message": str(error),
                        "seconds": round(time.time() - started, 1)}
        candidate = (data.get("candidates") or [{}])[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        usage = data.get("usageMetadata") or {}
        self._record(usage)
        return "".join(p.get("text", "") for p in parts if not p.get("thought")), {
            "prompt_tokens": usage.get("promptTokenCount"),
            "output_tokens": usage.get("candidatesTokenCount"),
            "thought_tokens": usage.get("thoughtsTokenCount"),
            "finish_reason": candidate.get("finishReason"), "max_tokens": sp.max_tokens,
            "model_version": data.get("modelVersion"), "response_id": data.get("responseId"),
            "seconds": round(time.time() - started, 1),
        }

    def parameters_for_items(self, items, *, sme=True):
        sp = copy.deepcopy(self.sp)
        self.SCRIPT.restrict_schema(sp.structured_outputs.json, items, sme=sme)
        return sp

    def chat(self, batch, sampling_params=None, items=None):
        self.last_response_info = []  # 실패한 호출이 앞 호출의 기록을 물려받지 않게 한다.
        sp = self.sp if sampling_params is None else sampling_params
        if items is not None:
            sp = self.parameters_for_items(items)
        with ThreadPoolExecutor(max_workers=max(1, min(self.WORKERS, len(batch)))) as pool:
            results = list(pool.map(lambda messages: self._one(messages, sp), batch))
        self.last_response_info = [info for _, info in results]
        return [text for text, _ in results]

    def retry_chat(self, batch, items=None):
        """복구는 제출 코드의 전략을 그대로 빌린다 — 24항목을 6개씩, 다시 1개씩 쪼개고
        재시도에서는 근거를 100자로 묶는다.

        여기서 다시 구현하면 API 경로와 제출 경로의 복구가 갈린다. 그러면 이 도구로 본 실패가
        서버에서 어떻게 복구되는지를 더는 말할 수 없다. `sp`를 VLLMRunner와 같은 모양으로
        둔 이유가 이것이다.
        """
        return self.SCRIPT.VLLMRunner.retry_chat(self, batch, items)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")  # 파이프에 붙은 파이썬은 로케일 인코딩으로 죽는다.
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", required=True, help="새 디렉터리. CSV·기록을 남긴다")
    parser.add_argument("--input", default=str(ROOT / "open/dev.jsonl"))
    parser.add_argument("--data-dir", default=str(ROOT / "open/data"))
    parser.add_argument("--limit", type=int, default=None, help="앞 N건만")
    parser.add_argument("--chunk", type=int, default=32, help="한 번에 병렬로 부를 건수")
    parser.add_argument("--max-chars", type=int, default=16000)
    parser.add_argument("--workers", type=int, default=4, help="동시 API 호출 수")
    parser.add_argument("--tpm", type=int, default=DEFAULT_TPM,
                        help=f"분당 입력 토큰 시작 추정치. 기본 {DEFAULT_TPM:,}은 2026-09-18 실측값이고,"
                             " 429가 실제 상한을 알려 주면 그것으로 갈아탄다")
    parser.add_argument("--model", default=os.environ.get("PPS_API_MODEL", DEFAULT_MODEL))
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--retries", type=int, default=4, help="429·5xx 재시도 횟수")
    parser.add_argument("--debug-responses", action="store_true",
                        help="원응답을 diagnostics.jsonl에 남긴다. tools/replay_run.py의 입력이 된다")
    parser.add_argument("--mock", action="store_true", help="키가 있어도 mock으로 돌린다")
    args = parser.parse_args(argv)

    key, source = (None, None) if args.mock else find_api_key()
    script = load_submission_script()
    if key:
        APIRunner.KEY, APIRunner.SCRIPT, APIRunner.MODEL = key, script, args.model
        APIRunner.WORKERS, APIRunner.TIMEOUT, APIRunner.RETRIES, APIRunner.TPM = (
            args.workers, args.timeout, args.retries, args.tpm)
        runner_cls = APIRunner
        # 분당 입력 토큰이 상한이라 200건은 시간 단위다. 돌리기 전에 알려 준다.
        notices = args.limit or sum(1 for _ in script.iter_records(args.input))
        each = TOKENS_PER_NOTICE * min(1.0, args.max_chars / 16000)
        minutes = notices * each / max(1, args.tpm)
        print(f"실제 모델: {args.model} · 키 출처 {source} · 동시 {args.workers}"
              f" · 분당 입력 토큰 {args.tpm:,}")
        print(f"  {notices}건 · 한도대로면 최소 {minutes:.0f}분. 줄이려면 --limit·--max-chars를 쓴다.")
    else:
        runner_cls = script.MockRunner
        print("API 키가 없다 → mock으로 돈다. 판정 정확도 검증이 아니다."
              if not args.mock else "--mock: 키를 무시하고 mock으로 돈다.")

    output = Path(args.output_dir)
    started = time.time()
    try:
        report = script.run(args.input, str(output / "submission.csv"), runner_cls,
                            limit=args.limit, chunk=args.chunk, max_chars=args.max_chars,
                            data_dir=args.data_dir, debug_responses=args.debug_responses,
                            model_dir="", quant=None, max_tokens=script.MAX_TOKENS,
                            seed=script.SEED, gpu_mem=0.92, tp=1)
    except Exception as error:
        print(f"error: {type(error).__name__}: {error}", file=sys.stderr)
        return 1

    runner = APIRunner.INSTANCE if key else None
    manifest = {
        "purpose": "local_api_validation_only", "mode": report["mode"],
        "is_contest_live_run": False, "counts_as_r4_normal_call": False,
        "api_model": args.model if key else None,
        "notices": report["건수"], "seconds": round(time.time() - started, 1),
        "code_sha256": report["code_sha256"], "input_sha256": report["input_sha256"],
        "input": script.record_path(args.input), "environment": report["environment"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": ("Google AI Studio가 호스팅한 같은 이름의 모델이다. 고정 리비전·양자화·"
                 "chat_template·thinking 설정이 평가 서버와 같다는 보장이 없다. "
                 "서버 점수·R4 정상 호출의 대체가 아니다."),
    }
    if runner:
        # 시작값이 아니라 실제로 지킨 상한을 적는다. 429를 만나면 도중에 바뀐다.
        manifest.update(api_calls=runner.calls, api_tokens=runner.tokens,
                        input_tokens_per_minute=runner.bucket.per_minute)
    (output / "api-run.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"{report['건수']}건 · mode={report['mode']} · 추론 {report['추론_s']}s"
          + (f" · API 호출 {runner.calls}회" if runner else ""))
    if runner:
        print(f"  입력 토큰 최대 {report['prompt_tokens_max']:,}"
              f" · 누적 입력 {runner.tokens['prompt']:,} · 누적 출력 {runner.tokens['output']:,}")
    print(f"  → {output}/submission.csv")
    truth = Path(args.input).resolve().with_name("dev_labels.csv")
    if truth.is_file():
        print(f"채점: python -X utf8 tools/score.py --truth {script.record_path(truth)} "
              f"--pred {output}/submission.csv --output-dir {output}/score")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
