#!/usr/bin/env python3
"""Reward for: Create a brand-new blank document titled "Weekly Standup Agenda".

Scores ONLY the task-introduced change: exactly one new document appears in the
`documents` map whose title == "Weekly Standup Agenda" and ownerId == "user-1".
The two pre-existing documents (doc-1 "Roadmap", doc-2 "Changelog") must remain
untouched. Over-action (creating extra docs, or mutating the existing ones) is
penalized.

Progressive scoring (max 1.0):
  +0.50  a new document with the expected title exists
  +0.20  that new document's ownerId == "user-1"
  +0.15  exactly one new document was created (no extra docs)
  +0.15  the two pre-existing documents are unchanged
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"
EXPECTED_TITLE = "weekly standup agenda"
EXPECTED_OWNER = "user-1"


def _read_sid():
    with open("/tmp/task_web_sid", "r") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _norm(s):
    return (s or "").strip().lower()


def _docs(state):
    docs = (state or {}).get("documents", {})
    return docs if isinstance(docs, dict) else {}


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)

    initial = data.get("initial_state", {}) or {}
    current = data.get("current_state", {}) or {}

    initial_docs = _docs(initial)
    current_docs = _docs(current)

    # New documents = present in current but not in initial (by doc ID).
    new_ids = [doc_id for doc_id in current_docs if doc_id not in initial_docs]
    new_docs = [current_docs[doc_id] for doc_id in new_ids]

    # The new docs that match the expected title.
    matching = [d for d in new_docs if _norm(d.get("title")) == EXPECTED_TITLE]

    score = 0.0

    # The over-action / cleanliness credits only apply once the core task has
    # actually been started (a matching new document exists). This guarantees the
    # untouched INITIAL state scores exactly 0.0 rather than earning credit for
    # "nothing changed".
    if matching:
        # (1) A new document with the expected title exists.
        score += 0.50

        # Pick the best-matching new doc for the owner check (prefer user-1).
        target = next(
            (d for d in matching if d.get("ownerId") == EXPECTED_OWNER), matching[0]
        )

        # (2) ownerId of the new document is user-1.
        if target.get("ownerId") == EXPECTED_OWNER:
            score += 0.20

        # (3) Exactly one new document was created (no over-action: extra docs).
        if len(new_ids) == 1:
            score += 0.15

        # (4) Pre-existing documents are unchanged (none deleted, none mutated).
        existing_unchanged = True
        for doc_id, doc in initial_docs.items():
            if doc_id not in current_docs:
                existing_unchanged = False
                break
            if current_docs[doc_id] != doc:
                existing_unchanged = False
                break
        if existing_unchanged:
            score += 0.15

    # Clamp.
    score = max(0.0, min(1.0, score))
    return round(score, 2)


if __name__ == "__main__":
    reward = compute_reward()
    print("REWARD: {}".format(reward))
