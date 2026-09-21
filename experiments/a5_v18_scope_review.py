"""One company call, separate scope observation consumed only by v18. Not adopted."""
from contextlib import contextmanager
from unittest.mock import patch

import script

INSTRUCTION = """

After all existing fields, report a separate review of the purchased scope in two fields.
Keep all existing field definitions unchanged. Do not decide violations.
- scope_review: general/competitive/other/unknown, with the same scope definitions above.
  Recheck the actual purchased deliverable against the supplied 고시 제2025-96호 catalogue,
  including the designated range and 특이사항 of each applicable candidate. A similar title,
  mention of a tool/component used to perform the work, or missing metadata code alone does
  not establish a classification. Check the actual AND/OR conditions using visible notice
  specifications; an unobserved alternative is not false. A referenced but unavailable
  specification is unobserved. For mixed purchases or unresolved applicable conditions,
  preserve unknown unless the purchased scope is established by the supplied evidence.
  Do not infer specifications from model names or outside knowledge. Do not use qualification
  restrictions or their absence to decide scope.
- scope_review_quote: one contiguous exact notice quotation identifying the purchased
  deliverable supporting this review, under the same length limit as scope_quote, or null
  if unobserved. Do not quote the catalogue as notice evidence or join separate spans.
"""


@contextmanager
def activate():
    original = script.company_size_schema

    def schema(**kwargs):
        result = original(**kwargs)
        props = dict(result['properties'])
        props.update(scope_review=props['scope'], scope_review_quote=props['scope_quote'])
        return {**result, 'properties': props, 'required': list(props)}

    with patch.object(script, 'company_size_schema', schema), \
            patch.object(script, 'COMPANY_SIZE_PROMPT', script.COMPANY_SIZE_PROMPT + INSTRUCTION):
        yield


def evaluate(facts, rec, max_chars):
    legacy, reason = script.verify_company_size(facts, rec, max_chars)
    out = dict(legacy)
    review, review_reason = {}, None
    if 'scope_review' in facts and 'scope_review_quote' in facts:
        copied = dict(facts, scope=facts['scope_review'], scope_quote=facts['scope_review_quote'])
        review, review_reason = script.verify_company_size(copied, rec, max_chars)
        if 'v18' in review:
            out['v18'] = review['v18']
    return out, reason, dict(legacy_reason=reason, review_reason=review_reason,
                            legacy_writes=legacy, review_writes=review,
                            v18_overwritten='v18' in review)


def verify_company_size(facts, rec, max_chars):
    out, reason, _ = evaluate(facts, rec, max_chars)
    return out, reason


def trace(facts, rec, max_chars):
    _, _, result = evaluate(facts, rec, max_chars)
    visible = script.build_context(rec, max_chars)
    quotes = {}
    for key in ('scope_quote', 'scope_review_quote'):
        raw = facts.get(key)
        restored = script.restore_spacing(raw, rec, visible) or raw
        quotes[key] = dict(raw=raw, restored=restored,
                           grounded=bool(restored and restored.strip() and restored in visible
                                         and any(restored in d['text'] for d in rec['docs'])))
    return dict(result, scope=facts['scope'], scope_review=facts.get('scope_review'),
                quotes=quotes, max_chars=max_chars)
