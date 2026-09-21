"""A8 후보 — company_size 프롬프트 뒤에 제공 지침 **제2조와 별표 1 원문만** 붙인다. 미채택.

RAG 주입 파이프라인 2단계(주입)다. 1단계 조회(`law_index`)는 `f04e8c7`로 들어왔다.
[착수서](../docs/tasks/a8-v20-annex-injection.md)가 목표·통과 조건·한계를 소유한다.

**바꾸는 것은 시스템 프롬프트 문자열 하나뿐이다.** 스키마·소비자·관측 게이트·조회 알고리즘·
운영 `script.py`는 그대로다. 새 검색기도 추가 호출도 금액 결정표도 만들지 않는다.
그래서 후보 OFF/ON 재생은 24항목 CSV가 바이트까지 같아야 한다(배선 검사).

**개선 여부는 미측정이다.** 고정 H4 혼합 비교에서 도달 가능한 v20 TP 상한은 **2**다 —
FN 024·131·134는 제안요청서 1건 탈락과 완전관측 false로 막히고(프롬프트가 못 바꾸는 입력 사실),
남은 FN 132는 `software_business=no`에서 막힌다. `reports/team-c/a8-v20-annex/`가 근거를 소유한다.

별표 하나가 v20 판정 규칙 전체는 아니다. 제2조②는 분리발주·분담이행 시 적용 제외를,
제3조는 적용 방법과 안내 의무를 따로 다룬다. 이번은 **제2조+별표의 추가 효과 실험**이며
완전한 법적 판정기가 아니다.
"""
from contextlib import contextmanager
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import script
from experiments import law_index

LAW = "중소 소프트웨어사업자의 사업 참여 지원에 관한 지침"
DATA_DIR = str(ROOT / "open/data")
# 출력 예약과 그에서 나오는 프롬프트 예산. **두 군이 같은 값을 쓴다.**
#
# 운영 `MAX_TOKENS=2048`은 H4 company 응답 실측(200건 전부 `stop`, max 494 · p95 389 토큰)의
# **4.15배**를 예약하고, 그 여유 때문에 프롬프트 예산이 14,272로 내려가 최대 공고 14,250에
# **22토큰**만 남는다. 그 자리에 블록을 넣으면 후보만 문서가 깎여 비교가 교란된다.
# 1,024는 관측 최댓값의 2.07배를 남기면서 예산을 15,296으로 올린다. **실측(고정 토크나이저):
# 블록은 200건 전부 586토큰이고, 최대 공고는 `PPS-DEV-189`의 후보 14,868 — 여유 428로
# 추가 축소 0/200이다.** H4에서 13,600자로 절단됐던 그 공고가 늘어난 예산에서 두 군 모두
# 절단이 풀려 control도 H4와 달라진다 — 기록한다. 나머지 199건의 control은 그대로다.
# 이 값은 파일럿 한정이다. 운영 채택은 단계별 예약이 필요해 `script.py` 수정이 따르며 별건이다.
OUTPUT_RESERVED = 1024
PROMPT_BUDGET = script.MAX_MODEL_LEN - OUTPUT_RESERVED - 64
# 별표 1의 세 하한. 80억·40억만 확인하면 중견기업 5년 미만의 20억원 행이 빠진 조각을 통과시킨다.
FLOORS = ("80억원", "40억원", "20억원")
# 지시는 영어, 원문은 한국어다. 법령은 공고 인용 근거가 아니며 null을 법적 추론으로 채우지 않는다.
HEADER = """

[Provided law reference — 중소 소프트웨어사업자의 사업 참여 지원에 관한 지침]
The text below is the provided law, copied verbatim. It is reference material, NOT a notice
document: never quote it in any quotation field, and never count it as the notice/RFP disclosure
that software_participation_quote asks for. It cannot make an unobserved document observed.
If the visible notice and RFP state no participation clause, still return null; do not derive one
from these amounts. Do not output an eligibility decision, an applicable floor, or any new field.
Use it only to recognize an actual 참여제한 하한 disclosure or exception when a document states one.
"""


def segments(data_dir: str = DATA_DIR):
    """제2조와 별표 1을 조회한다. 조각이 없거나 원문과 어긋나면 실행을 중단한다."""
    name = law_index.resolve_law(LAW, data_dir)
    if name is None:
        raise ValueError("제공 법령에서 지침을 찾지 못했다: " + LAW)
    raw = law_index.laws(data_dir)[name]
    found = {"제2조": law_index.article(LAW, "제2조", data_dir=data_dir),
             "별표 1": law_index.annex(LAW, 1, data_dir=data_dir)}
    for label, segment in found.items():
        if segment is None or not segment.text.strip():
            raise ValueError(f"빈 조각으로는 주입하지 않는다: {label}")
        if segment.text not in raw:
            raise ValueError(f"제공 원문의 부분문자열이 아니다: {label}")
    missing = [floor for floor in FLOORS if floor not in found["별표 1"].text]
    if missing:
        raise ValueError("별표 1에서 하한 행이 빠졌다: " + ", ".join(missing))
    return found["제2조"], found["별표 1"]


@lru_cache(maxsize=4)
def block(data_dir: str = DATA_DIR) -> str:
    """프롬프트 끝에 붙일 참조 블록. 지시 + 두 조각 원문뿐이다."""
    article, annex = segments(data_dir)
    return HEADER + "\n" + article.text + "\n\n" + annex.text + "\n"


@contextmanager
def activate(data_dir: str = DATA_DIR):
    """company_size 프롬프트만 임시로 교체한다. 예외·종료 시 원본으로 복원한다."""
    with patch.object(script, "COMPANY_SIZE_PROMPT", script.COMPANY_SIZE_PROMPT + block(data_dir)):
        yield


class TokenizerRunner:
    """고정 리비전의 토크나이저와 제출 chat template만으로 토큰을 센다. 생성하지 않는다.

    `VLLMRunner.count_tokens`와 같은 호출이다. 가중치도 GPU도 필요 없으므로 착수서 §4.3의
    CPU 경로가 된다. `chat_template_sha256`을 같이 남겨 GPU 회차의 환경 기록과 대조한다.

    **서버 고정 `transformers` 5.14.1이 필요하다.** 4.x는 이 모델의 `tokenizer_config.json`을
    못 읽고 `_set_model_specific_special_tokens`에서 터진다. torch는 필요 없다.
    """

    MODE = "tokenizer_only"
    TOKEN_COUNT = "actual"
    load_seconds = 0.0

    def __init__(self, tokenizer_dir: str):
        from transformers import AutoTokenizer  # 지연 import — 검사·수집 경로는 필요 없다.
        if Path(tokenizer_dir).name != script.MODEL_REVISION:
            raise ValueError("고정 리비전 snapshot 디렉터리가 아니다: " + tokenizer_dir)
        self.tok = AutoTokenizer.from_pretrained(tokenizer_dir)
        self.environment = {"tokenizer_dir": Path(tokenizer_dir).name,
                            "transformers": __import__("transformers").__version__,
                            "chat_template_sha256": hashlib.sha256(
                                str(self.tok.chat_template).encode("utf-8")).hexdigest()}

    def count_tokens(self, messages):
        ids = self.tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=True,
                                           enable_thinking=False)
        if hasattr(ids, "keys") and "input_ids" in ids:
            ids = ids["input_ids"]
        return len(ids)

    def block_tokens(self, data_dir: str = DATA_DIR) -> int:
        """참조 블록만의 토큰 비용. 같은 user 메시지에서 두 system 프롬프트의 차이로 센다."""
        empty = [{"role": "system", "content": script.COMPANY_SIZE_PROMPT},
                 {"role": "user", "content": ""}]
        with_block = [{"role": "system", "content": script.COMPANY_SIZE_PROMPT + block(data_dir)},
                      {"role": "user", "content": ""}]
        return self.count_tokens(with_block) - self.count_tokens(empty)


def _visible_sha256(rec, max_chars: int) -> str:
    return hashlib.sha256(script.build_context(rec, max_chars).encode("utf-8")).hexdigest()


def budget_report(records, runner, products=(), *, max_chars: int, budget: int = PROMPT_BUDGET,
                  data_dir: str = DATA_DIR):
    """공고별 control/후보 예산을 **러너의 실제 토크나이저와 chat template**로 센다.

    통과 조건은 추가 축소 0건과 두 군 공고 본문 동일이다. control에 이미 있던 절단은 따로 센다.
    mock/글자 환산 러너는 조건을 채워도 `budget_safety_evidence`가 거짓이다.
    `budget`은 두 군 공통이다. 운영 `script.PROMPT_BUDGET`과의 차이도 함께 남긴다.
    """
    if HEADER in script.COMPANY_SIZE_PROMPT:
        raise ValueError("control 예산은 참조 블록 밖에서 센다")
    arms = (("control", script.COMPANY_SIZE_PROMPT),
            ("candidate", script.COMPANY_SIZE_PROMPT + block(data_dir)))
    rows = []
    for rec in records:
        company_rec = {**rec, "meta": {k: v for k, v in rec.get("meta", {}).items() if k != "조항호내용"}}
        measured = {}
        for arm, prompt in arms:
            messages, tokens, chars = script.fit_to_budget(company_rec, prompt, runner, max_chars,
                                                           budget=budget, products=products)
            measured[arm] = dict(prompt_tokens=tokens, max_chars=chars, shrunk=chars < max_chars,
                                 visible_sha256=_visible_sha256(company_rec, chars),
                                 messages_sha256=hashlib.sha256(json.dumps(
                                     messages, sort_keys=True, ensure_ascii=False).encode()).hexdigest())
        rows.append(dict(id=rec["id"], **measured,
                         additional_shrink=measured["candidate"]["max_chars"] < measured["control"]["max_chars"],
                         same_visible=measured["candidate"]["visible_sha256"] == measured["control"]["visible_sha256"],
                         added_tokens=measured["candidate"]["prompt_tokens"] - measured["control"]["prompt_tokens"],
                         complete_observation=rec.get("input_completeness", {}).get("완전관측") is True))
    token_count = getattr(runner, "TOKEN_COUNT", "test_double")
    shrink = [r["id"] for r in rows if r["additional_shrink"]]
    differs = [r["id"] for r in rows if not r["same_visible"]]
    passes = not shrink and not differs
    reference = block(data_dir)
    return dict(records=len(rows), max_chars=max_chars, prompt_budget=budget,
                output_reserved=OUTPUT_RESERVED, submission_prompt_budget=script.PROMPT_BUDGET,
                submission_max_tokens=script.MAX_TOKENS, model_revision=script.MODEL_REVISION,
                token_count_kind=token_count,
                headroom_over_worst_control=budget - max((r["control"]["prompt_tokens"] for r in rows),
                                                         default=0),
                chat_template_sha256=getattr(runner, "environment", {}).get("chat_template_sha256"),
                reference_chars=len(reference), reference_sha256=hashlib.sha256(
                    reference.encode("utf-8")).hexdigest(),
                added_tokens_min=min((r["added_tokens"] for r in rows), default=None),
                added_tokens_max=max((r["added_tokens"] for r in rows), default=None),
                additional_shrink=shrink, visible_differs=differs,
                control_truncated=[r["id"] for r in rows if r["control"]["shrunk"]],
                candidate_truncated=[r["id"] for r in rows if r["candidate"]["shrunk"]],
                conditions_pass=passes,
                budget_safety_evidence=passes and token_count == "actual",
                note="Prompt-only injection. Token counts come from this runner; a non-actual "
                     "count is not budget evidence and no character estimate substitutes for it.",
                rows=rows)
