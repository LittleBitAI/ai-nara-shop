"""B9 v24 — the budget axis rebuilt field by field, used to raise v24.

Post-model step only; swap in with `tools/replay_run.py --candidate`. No model call.

The operating `amount_diff()` is out of `AXES` (see "왜 예산 축을 껐나" in `script.py`).
It compared any budget-ish amount against either registered field and so let a match
on one field erase a mismatch on the other. This module keeps the axis separate from
the operating code and applies four conditions taken from what the amounts mean
(`docs/tasks/b-v24-budget-axis.md`):

1. Field by field — an estimate (`추정가격`) is compared with `입찰추정가격`; a total
   (`배정예산`, `추정금액`, bid-target and project totals) with `배정예산금액`. Each amount
   is judged alone, so a match elsewhere on the line never erases its mismatch. An amount
   equal to the *other* field is the same money under the other VAT basis
   (`사업예산 27,200,000` with registered estimate 27,200,000) and is not a mismatch.
2. Display rounding — two amounts are equal when one is the other shown at a coarser
   unit (10/100/1,000 won, read from trailing zeros), or they differ by the 1 won left
   by a VAT back-calculation.
3. Bid scope — when the notice states a bid-target amount (`입찰대상금액`, `입찰금액`,
   `용역예정금액`, `추정금액`), project totals (`사업예산`…) are not compared:
   `배정예산금액` is what was budgeted for this bid.
4. Unit-price contract — when the notice says it is a unit-price contract, `기초금액`
   and `추정가격` are per-unit, so only the totals are compared. A registered amount
   below `MIN_AMOUNT` is a unit price too and is not compared with a notice total.

`기초금액` has no registered field. It is a cost-reviewed price (지방 집행기준, 적격심사
예정가격 제3절 1·2), usually set below the budget, so it counts only when it exceeds
`배정예산금액` — a base price above the allocated budget.

These refinements beyond the task's first design came from reading the unlabeled fires;
`reports/team-b/b9-v24-budget-axis/README.md` records the counts before and after.

On a mismatch v24 becomes 1 even where the model said 0, quoting the notice amount.
Everything else is the operating `postprocess()` unchanged.

Replay:
    python -X utf8 tools/replay_run.py --case reports/runs/colab-1789902969401579900/dev-debug \
      --candidate experiments/b_v24_budget_axis_candidate.py --output-dir <new path>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]

_ = r"[ \t　]*"          # spacing inside one line; a quote never crosses a line
ESTIMATE, BASIC, BUDGET, BID, PROJECT = "estimate", "basic", "budget", "bid", "project"
# `추정금액` is this contract's total, not an estimate: 국가계약법 시행규칙 제2조제2호
# defines it as 추정가격 + 부가가치세 + 관급재료.
LABELS = (
    (ESTIMATE, rf"추{_}정{_}가{_}격"),
    (BID, rf"입{_}찰{_}대{_}상{_}금{_}액|입{_}찰{_}금{_}액|(?:용{_}역|구{_}매|공{_}사){_}예{_}정{_}금{_}액"
          rf"|추{_}정{_}금{_}액"),
    (PROJECT, rf"총{_}사{_}업{_}비|사{_}업{_}(?:예{_}산|금{_}액)"),
    (BASIC, rf"기{_}초{_}(?:금{_}액|가{_}격)"),
    (BUDGET, rf"배{_}정{_}(?:예{_}산(?:{_}금{_}액)?|금{_}액)"),
)
KIND = {f"k{i}": kind for i, (kind, _pattern) in enumerate(LABELS)}
AMOUNT = r"(?P<amount>\d{1,3}(?:,\d{3})+|\d{5,})"
LABELED = re.compile(
    "(?:" + "|".join(f"(?P<k{i}>{pattern})" for i, (_kind, pattern) in enumerate(LABELS)) + ")"
    + rf"{_}(?:\([^)\n]{{0,15}}\))?{_}[:：]?{_}(?:금{_})?" + AMOUNT + rf"{_}원")
# `추정가격 230,000,000원 미만` is a threshold in a rule, not this notice's price.
THRESHOLD = re.compile(rf"{_}(?:이상|미만|이하|초과)")
# `사업예산: 1,750,000원 × 18명 = 31,500,000원` — the total is after `=`.
FORMULA = re.compile(rf"{_}[×xX*][^=\n]{{0,30}}={_}(?:금{_})?" + AMOUNT + rf"{_}원")
UNIT_PRICE = re.compile(rf"단{_}가{_}(?:계{_}약|입{_}찰|견{_}적)")
FIELD = {ESTIMATE: "입찰추정가격", BASIC: "배정예산금액", BUDGET: "배정예산금액",
         BID: "배정예산금액", PROJECT: "배정예산금액"}
MIN_AMOUNT = 1_000_000       # same floor as `amount_diff`: fees and unit prices sit below it
MAX_DISPLAY_UNIT = 1_000     # budgets are shown truncated to 1,000 won at most


def baseline():
    """The submission module the replayer loaded; standalone, the repo's `script.py`."""
    submitted = sys.modules.get("submission")
    if submitted is not None:
        return submitted
    import importlib.util
    spec = importlib.util.spec_from_file_location("baseline_script", ROOT / "script.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["submission"] = module
    spec.loader.exec_module(module)
    return module


def _display_unit(value: int) -> int:
    unit = 1
    while unit < MAX_DISPLAY_UNIT and value % (unit * 10) == 0:
        unit *= 10
    return unit


def same_amount(shown: int, registered: int) -> bool:
    """Condition 2: equal up to display rounding or the 1 won VAT back-calculation residual."""
    gap = abs(shown - registered)
    return gap <= 1 or gap < max(_display_unit(shown), _display_unit(registered))


def _as_int(value) -> Optional[int]:
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def budget_mismatch(rec: Dict[str, Any]) -> Optional[str]:
    """The first notice amount that differs from its own registered field, or None."""
    meta = rec.get("meta") or {}
    registered = {field: _as_int(meta.get(field)) for field in set(FIELD.values())}
    found = []
    for doc in rec.get("docs") or []:
        text = doc.get("text") or ""
        for match in LABELED.finditer(text):
            rest = text[match.end():]
            if THRESHOLD.match(rest):
                continue
            formula = FORMULA.match(rest)
            amount = _as_int((formula or match).group("amount"))
            quote = text[match.start():match.end() + (formula.end() if formula else 0)]
            kind = next(KIND[group] for group in KIND if match.group(group))
            found.append((kind, amount, quote.strip()))
    kinds = {kind for kind, _amount, _quote in found}
    unit_price = any(UNIT_PRICE.search(doc.get("text") or "") for doc in rec.get("docs") or [])
    for kind, amount, quote in found:
        if kind == PROJECT and BID in kinds:
            continue                                    # condition 3
        if unit_price and kind in (ESTIMATE, BASIC):
            continue                                    # condition 4
        own = registered[FIELD[kind]]                   # condition 1
        if amount is None or own is None or amount < MIN_AMOUNT or own < MIN_AMOUNT:
            continue
        if same_amount(amount, own) or (kind == BASIC and amount < own):
            continue
        if any(same_amount(amount, other) for other in registered.values() if other):
            continue                                    # same money, other VAT basis
        return quote
    return None


def postprocess(judgment: Dict[str, Dict[str, Any]], rec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    base = baseline()
    out = base.postprocess(judgment, rec)
    if out["v24"]["위반여부"] == 1:
        return out
    quote = budget_mismatch(rec)
    if not quote:
        return out
    for doc in rec["docs"]:
        cleaned = base.clean_evidence(quote, doc["text"])
        if cleaned:
            out["v24"] = {"위반여부": 1, "근거문구": cleaned}
            break
    return out
