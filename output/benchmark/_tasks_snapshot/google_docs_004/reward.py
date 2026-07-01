"""Reward for: Switch the document list to list view instead of the grid of thumbnails.

Scoring (exact state checks only — objective UI flag, no LLM judge needed):
  - 1.0  ui.documentListView == "list" AND documents unchanged (no over-action)
  - 0.0  ui.documentListView still "grid" (not done)
  - partial penalties if the documents map was altered (over-action)
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _docs_equal(a, b):
    """Compare the documents map for equality (no add/remove/modify)."""
    if not isinstance(a, dict) or not isinstance(b, dict):
        return a == b
    if set(a.keys()) != set(b.keys()):
        return False
    for k in a:
        if a[k] != b[k]:
            return False
    return True


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)

    initial_state = data.get("initial_state", {}) or {}
    current_state = data.get("current_state", {}) or {}

    cur_ui = current_state.get("ui", {}) or {}
    init_docs = initial_state.get("documents", {}) or {}
    cur_docs = current_state.get("documents", {}) or {}

    list_view = cur_ui.get("documentListView") == "list"

    # The core task: list view must be selected.
    if not list_view:
        return 0.0

    score = 1.0

    # Over-action penalty: documents must be untouched (none added/removed/modified).
    if not _docs_equal(init_docs, cur_docs):
        score -= 0.5

    if score < 0.0:
        score = 0.0
    return round(score, 2)


if __name__ == "__main__":
    try:
        reward = compute_reward()
    except Exception as e:
        print("ERROR computing reward:", e)
        reward = 0.0
    print("REWARD: " + str(reward))
