#!/usr/bin/env python3
"""Reward for: switch the editor to viewing (read-only) mode for the "Legal Terms" document.

Task-introduced change: ui.viewMode must become "viewing".
Invariants (penalize over-action): document content/title and currentDocId unchanged.

Scoring is anchored on the actual task-introduced change so the untouched
initial state scores exactly 0.0; invariants only act as over-action guards.
"""
import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"


def read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    sid = read_sid()
    data = fetch_state(sid)
    initial = data.get("initial_state", {}) or {}
    current = data.get("current_state", {}) or {}

    init_ui = initial.get("ui", {}) or {}
    cur_ui = current.get("ui", {}) or {}
    init_docs = initial.get("documents", {}) or {}
    cur_docs = current.get("documents", {}) or {}

    # --- Primary criterion: viewMode flipped to "viewing" ---
    # This IS the task-introduced change; untouched initial (viewMode=="editing")
    # therefore scores 0.0.
    view_mode = cur_ui.get("viewMode")
    if view_mode == "viewing":
        score = 1.0
    elif view_mode == "suggesting":
        # left editing mode but picked the wrong target mode -> partial credit
        score = 0.3
    else:
        # "editing" or missing -> not done
        score = 0.0

    # --- Over-action guard: currentDocId must be unchanged (still on the doc) ---
    if cur_ui.get("currentDocId") != init_ui.get("currentDocId"):
        score = min(score, 0.5)

    # --- Over-action guard: document content/title must not be modified ---
    docs_unchanged = set(cur_docs.keys()) == set(init_docs.keys())
    if docs_unchanged:
        for doc_id, init_doc in init_docs.items():
            cur_doc = cur_docs.get(doc_id, {})
            if cur_doc.get("content") != init_doc.get("content") or cur_doc.get(
                "title"
            ) != init_doc.get("title"):
                docs_unchanged = False
                break
    if not docs_unchanged:
        score = min(score, 0.5)

    score = max(0.0, min(1.0, round(score, 2)))
    print("REWARD:", score)


if __name__ == "__main__":
    main()
