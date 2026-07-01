"""Reward for: Unstar the "Vacation Itinerary" document.

Task-introduced change: documents[doc-1].starred  true -> false.
Distractors that must stay UNCHANGED:
  - doc-2 "Expense Report"  starred=true  (stays true)
  - doc-3 "Reading List"    starred=false (stays false)

Scoring (progressive 0.0-1.0):
  - Core (1.0): the "Vacation Itinerary" doc is unstarred (starred == False).
  - Over-action penalty: if any distractor doc's starred flag was flipped from
    its initial value, the score is reduced (0.5 off per flipped distractor).
Pure exact-state checks; no LLM judge needed (nothing subjective here).
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


def _find_doc_by_title(documents, title):
    title_l = title.strip().lower()
    for doc in documents.values():
        if str(doc.get("title", "")).strip().lower() == title_l:
            return doc
    return None


def compute_reward():
    sid = _read_sid()
    data = _get_state(sid)
    current = data.get("current_state", {}) or {}
    cur_docs = current.get("documents", {}) or {}

    score = 0.0

    # --- Core: "Vacation Itinerary" must be unstarred -------------------------
    target = _find_doc_by_title(cur_docs, "Vacation Itinerary")
    if target is None:
        print("Target doc 'Vacation Itinerary' not found in current state.")
        print("REWARD: 0.0")
        return
    if target.get("starred") is False:
        score += 1.0
    else:
        print("'Vacation Itinerary' is still starred (starred != False).")

    # --- Over-action penalty: distractor stars must be unchanged --------------
    # Expected unchanged: "Expense Report" starred=True, "Reading List" starred=False.
    distractor_expected = {
        "Expense Report": True,
        "Reading List": False,
    }
    for d_title, expected_starred in distractor_expected.items():
        doc = _find_doc_by_title(cur_docs, d_title)
        if doc is None:
            # Distractor doc went missing -> destructive over-action.
            print(f"Distractor doc '{d_title}' missing -> penalty.")
            score -= 0.5
        elif doc.get("starred") is not expected_starred:
            print(f"Distractor doc '{d_title}' starred changed -> penalty.")
            score -= 0.5

    score = max(0.0, min(1.0, score))
    print(f"REWARD: {score}")


if __name__ == "__main__":
    compute_reward()
