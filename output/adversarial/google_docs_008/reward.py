"""Reward for: Set the editor zoom to 150% for the "Blueprint" document.

Task-introduced change: ui.zoom goes from 100 -> 150 while staying on doc-1.
Scoring is a pure exact-state check (no LLM judge needed):
  - 0.7  ui.zoom == 150 (the core change)
  - 0.3  no over-action: still on doc-1 and the Blueprint document content is unchanged
Initial state (zoom==100, untouched) scores 0.0; fully-completed state scores 1.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _get_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def compute_reward():
    sid = _read_sid()
    data = _get_state(sid)

    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}

    cur_ui = current.get("ui", {}) or {}
    init_ui = initial.get("ui", {}) or {}

    cur_docs = current.get("documents", {}) or {}
    init_docs = initial.get("documents", {}) or {}

    score = 0.0

    # --- Locate the Blueprint document (by title) ---
    blueprint_id = None
    for doc_id, doc in init_docs.items():
        if (doc or {}).get("title") == "Blueprint":
            blueprint_id = doc_id
            break
    if blueprint_id is None:
        # fall back to the documented ground-truth id
        blueprint_id = "doc-1"

    # --- Core change: zoom == 150 (0.7) ---
    # This is the only task-introduced change. On the initial state (zoom==100)
    # this contributes 0.0, so the not-done state scores 0.0 overall.
    cur_zoom = cur_ui.get("zoom")
    try:
        cur_zoom_val = int(cur_zoom)
    except (TypeError, ValueError):
        cur_zoom_val = None

    init_zoom = init_ui.get("zoom", 100)

    if cur_zoom_val == 150:
        score += 0.7
    elif cur_zoom_val is not None and cur_zoom_val != init_zoom:
        # zoom was changed but not to 150 -> partial credit for engagement
        score += 0.2

    # The no-over-action credit below is only meaningful once the editor has
    # actually been touched; gating it on a zoom change keeps the untouched
    # initial state at exactly 0.0 (otherwise "doc unchanged" would award credit
    # for doing nothing).
    if cur_zoom_val is not None and cur_zoom_val != init_zoom:
        # --- No over-action: still on the Blueprint doc (0.15) ---
        if cur_ui.get("currentDocId") == init_ui.get("currentDocId", blueprint_id):
            score += 0.15

        # --- No over-action: Blueprint document content/title unchanged (0.15) ---
        init_doc = init_docs.get(blueprint_id, {}) or {}
        cur_doc = cur_docs.get(blueprint_id, {}) or {}
        content_unchanged = init_doc.get("content") == cur_doc.get("content")
        title_unchanged = init_doc.get("title") == cur_doc.get("title")
        # also ensure no documents were added/removed (over-action)
        docs_set_unchanged = set(cur_docs.keys()) == set(init_docs.keys())
        if content_unchanged and title_unchanged and docs_set_unchanged:
            score += 0.15

    # Clamp
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0
    return round(score, 2)


if __name__ == "__main__":
    reward = compute_reward()
    print("REWARD: " + str(reward))
