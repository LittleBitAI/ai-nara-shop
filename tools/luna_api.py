"""Label one notice with the OpenAI Responses API. Used in-process by `tools/label_bundle.py run --api`.

Label-generation stage only (R6): no tools are sent, so the model cannot search the web. It is outside the
submission ZIP and `script.py` never imports it (R7). Needs OPENAI_API_KEY.

Caching. The request carries two input messages: a developer message with the bundle's `prompt.md`
(instructions, item table, statute excerpt, rulings — identical on every call) marked with an explicit cache
breakpoint, then a user message with the notice. With `prompt_cache_options.mode = explicit` only that
breakpoint is written, so every later call within the 30-minute TTL reads the static context from cache.

  python -X utf8 tools/luna_api.py --effort low     # one tiny call to check the key
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

URL = "https://api.openai.com/v1/responses"
# USD per 1M tokens, gpt-6-luna Standard (developers.openai.com, 2026-09-25).
PRICE = {"input": 0.10, "cached": 0.01, "cache_write": 0.125, "output": 0.50}


def cost(usage):
    details = usage.get("input_tokens_details") or {}
    cached, written = details.get("cached_tokens", 0), details.get("cache_write_tokens", 0)
    plain = usage.get("input_tokens", 0) - cached - written
    return (plain * PRICE["input"] + cached * PRICE["cached"] + written * PRICE["cache_write"]
            + usage.get("output_tokens", 0) * PRICE["output"]) / 1e6


def body(context, notice, model, effort):
    return {
        "model": model, "reasoning": {"effort": effort}, "store": False,
        "prompt_cache_options": {"mode": "explicit", "ttl": "30m"},
        "input": [
            {"role": "developer", "content": [{"type": "input_text", "text": context,
                                               "prompt_cache_breakpoint": {"mode": "explicit"}}]},
            {"role": "user", "content": [{"type": "input_text", "text": notice}]},
        ],
    }


def post(payload, timeout, retries=3):
    request = urllib.request.Request(URL, data=json.dumps(payload).encode("utf-8"), headers={
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            if exc.code not in (429, 500, 502, 503) or attempt == retries - 1:
                raise ValueError(f"HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise ValueError(f"request failed: {exc}") from exc
        time.sleep(10 * (attempt + 1))


def ask(context, notice, *, model="gpt-6-luna", effort="high", timeout=900):
    """Return a `claude -p --output-format json` style envelope string, so label_bundle records it unchanged."""
    began = time.perf_counter()
    data = post(body(context, notice, model, effort), timeout)
    text = "".join(part.get("text", "") for item in data.get("output", []) if item.get("type") == "message"
                   for part in item.get("content", []) if part.get("type") == "output_text")
    usage = data.get("usage") or {}
    return json.dumps({"type": "result", "result": text, "usage": usage, "num_turns": 1,
                       "total_cost_usd": round(cost(usage), 6), "model": data.get("model"),
                       "response_id": data.get("id"),
                       "duration_ms": int((time.perf_counter() - began) * 1000)}, ensure_ascii=False)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default="gpt-6-luna")
    parser.add_argument("--effort", default="low")
    args = parser.parse_args()
    print(ask("Answer with the JSON the user asks for and nothing else. " * 200, 'Reply with {"ok": 1}.',
              model=args.model, effort=args.effort))
    return 0


if __name__ == "__main__":
    sys.exit(main())
