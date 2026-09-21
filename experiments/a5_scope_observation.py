"""A5 H3: expose catalogue-condition observations inside the existing company call."""
from contextlib import contextmanager
from unittest.mock import patch

import script

INSTRUCTION = """Before choosing scope, output the following catalogue observations in this order:
- scope_product_code: a 10-digit code copied from a supplied catalogue candidate identifying
  the actual purchased deliverable, or null if unresolved. A metadata match only nominates a
  candidate. Consider service meaning too; lack of a metadata code does not exclude a service.
  For mixed purchases, identify a designated deliverable actually being purchased, not a tool,
  packaging, incidental part, or a product merely mentioned in a repair/maintenance contract.
- scope_condition_quote and scope_condition_quote_2: up to two exact contiguous notice spans
  supporting or contradicting that candidate's applicable 특이사항 conditions; null if unseen.
  Each span is at most 240 characters. Do not copy catalogue text as notice evidence, concatenate
  spans, or infer specifications from a model name using outside knowledge.
- scope_condition_state: met/contradicted/unobserved/not_required. Evaluate the supplied row's
  actual AND/OR logic. An OR condition is contradicted only if every alternative is contradicted;
  an unknown alternative cannot be treated as false. not_required means a selected row has no
  특이사항; no selected row means unobserved. met requires evidence for the applicable conditions.
  Keep actual configuration separate from supported maximum capacity, base from boosted
  frequency, own weight from loaded/takeoff weight, and altitude from horizontal distance.
  A referenced but unavailable specification is unobserved even if input completeness is true.
  If two spans cannot establish the required conditions, preserve unobserved, not guessed met.
Then choose scope using these observations and the purchased deliverable. A conditional
candidate with unresolved conditions does not establish competitive scope. A contradicted
candidate does not make the whole mixed procurement general when another designated
deliverable applies. Do not invent that other deliverable to avoid an unknown result.
All other qualification, exception and software observations retain their original meanings.

"""


@contextmanager
def activate():
    """Temporary experiment only; every existing consumer and production source is unchanged."""
    original_schema = script.company_size_schema

    def schema(**kwargs):
        result = original_schema(**kwargs)
        quote = {"type": ["string", "null"], "maxLength": 240}
        props = {
            "scope_product_code": {"type": ["string", "null"], "maxLength": 10},
            "scope_condition_quote": quote,
            "scope_condition_quote_2": quote,
            "scope_condition_state": {"type": "string", "enum": ["met", "contradicted", "unobserved", "not_required"]},
            **result["properties"],
        }
        return {**result, "properties": props, "required": list(props)}

    with patch.object(script, 'COMPANY_SIZE_PROMPT', INSTRUCTION + script.COMPANY_SIZE_PROMPT), \
            patch.object(script, 'company_size_schema', schema):
        yield


def trace(facts, rec, chars, products):
    """Check source grounding, not semantic truth. These diagnostics never change verdicts."""
    visible = script.build_context(rec, chars)
    candidates = script.sme_product_lookup(rec, visible, products)
    codes = {p['세부품명번호'] for p in candidates['일치후보']}
    codes.update(p[0] for p in candidates['서비스보조목록'])
    code = facts['scope_product_code']
    selected = next((p for p in products if p['세부품명번호'] == code), None)
    quote_checks = {}
    for key in ('scope_condition_quote', 'scope_condition_quote_2'):
        quote = facts[key]
        quote = script.restore_spacing(quote, rec, visible) or quote
        quote_checks[key] = None if quote is None else bool(quote.strip() and quote in visible
                            and any(quote in d['text'] for d in rec['docs']))
    state = facts['scope_condition_state']
    return dict(code=code, code_in_supplied_candidates=code in codes if code else False,
                condition=selected['특이사항'] if selected else None, state=state,
                quote_grounding=quote_checks,
                competitive_without_condition_support=(facts['scope'] == 'competitive' and
                    (not selected or code not in codes or
                     (bool(selected['특이사항']) and (state != 'met' or
                      not any(v is True for v in quote_checks.values()) or False in quote_checks.values())) or
                     (not selected['특이사항'] and state != 'not_required'))))
