"""
LOCAL judge shim for the web-only harness.

Drop-in replacement for utils/reward_judge.py's public API, with ONE difference:
the model is env-configurable so a plain OpenAI key works. The shipped
reward_judge.py hardcodes _MODEL="claude-sonnet-4-5" (expects a Claude proxy via
OPENAI_BASE_URL); locally we usually only have a standard OpenAI key, so we default
to gpt-4o and let it be overridden.

reward.py does `from reward_judge import call_llm_judge`. When this directory is
first on PYTHONPATH, this module shadows utils/reward_judge.py for local runs only.
The real, locked-down file is never modified.

Config (env):
  OPENAI_API_KEY        required for any judge call
  OPENAI_BASE_URL       optional; set to a proxy to use a non-OpenAI model
  CUA_GYM_JUDGE_MODEL   judge model (default: gpt-4o)
"""
import json
import os
import re

_MODEL = os.getenv("CUA_GYM_JUDGE_MODEL", "gpt-4o")
_TEMPERATURE = 0.0
_MAX_RETRIES = 3

_SYSTEM_PROMPT = """\
You are a precise task completion evaluator for computer-use agent training.

Your job: determine whether a web application's current state matches the expected
outcome described in the success criteria. Score on a 0.0-1.0 scale.

Rules:
- Semantic equivalence is acceptable (e.g., "SD-USA" = "San Diego, USA")
- Minor formatting differences are acceptable (extra spaces, capitalization)
- Missing information or wrong information scores 0.0 for that criterion
- Partial completion gets proportional partial credit
- Be strict: do not give credit for vaguely related content

Respond with ONLY a JSON object:
{"score": <float 0.0-1.0>, "reasoning": "<brief explanation of each criterion>"}
"""


def call_llm_judge(
    task_instruction: str,
    success_criteria: str,
    state_excerpt: str,
    max_tokens: int = 300,
) -> float:
    """Judge semantic / subjective criteria. Returns float in [0.0, 1.0]."""
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        print("LLM_JUDGE_ERROR: No OPENAI_API_KEY found")
        return 0.0

    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    user_prompt = f"""TASK: {task_instruction}

SUCCESS CRITERIA:
{success_criteria}

STATE TO EVALUATE:
{state_excerpt[:6000]}

Score 0.0-1.0 based on how well the state meets the success criteria.
Respond with JSON only: {{"score": <float>, "reasoning": "<brief>"}}"""

    last_error = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=_TEMPERATURE,
                max_tokens=max_tokens,
            )
            text = resp.choices[0].message.content.strip()
            try:
                score = float(json.loads(text)["score"])
            except (json.JSONDecodeError, KeyError, ValueError):
                m = re.search(r'"?score"?\s*:\s*([\d.]+)', text)
                score = float(m.group(1)) if m else 0.0
            score = max(0.0, min(1.0, score))
            print(f"LLM_JUDGE[{_MODEL}]: score={score} | {text[:200]}")
            return score
        except Exception as e:  # noqa: BLE001
            last_error = e
            if attempt < _MAX_RETRIES:
                import time
                time.sleep(1.0 * (attempt + 1))
                continue
    print(f"LLM_JUDGE_ERROR: all attempts failed. Last error: {last_error}")
    return 0.0


def call_vision_judge(*args, **kwargs) -> float:
    """Gmail tasks don't use vision. Present so imports never break."""
    print("VISION_JUDGE: not supported in local web-only harness; returning 0.0")
    return 0.0
