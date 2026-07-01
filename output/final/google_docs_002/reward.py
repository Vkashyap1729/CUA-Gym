"""Reward for: Rename my "Untitled document" to "Sprint Retrospective Notes".

Scores ONLY the task-introduced change: documents[doc-1].title must become
"Sprint Retrospective Notes". The distractor docs (doc-2 "Sprint Planning",
doc-3 "Project Proposal") must be left unchanged (over-action penalty).

Pure exact-state check — no LLM judge needed (title is an exact string).
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"

TARGET_DOC = "doc-1"
TARGET_TITLE = "Sprint Retrospective Notes"
INITIAL_TITLE = "Untitled document"

# Distractor docs that must remain untouched.
DISTRACTORS = {
    "doc-2": "Sprint Planning",
    "doc-3": "Project Proposal",
}


def _norm(s):
    return (s or "").strip()


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current_state", {}) or {}
    documents = current.get("documents", {}) or {}

    reward = 0.0

    # --- Main criterion: doc-1 renamed to the target title (exact, case-insensitive). ---
    target_doc = documents.get(TARGET_DOC, {}) or {}
    title = _norm(target_doc.get("title"))

    if title.lower() == TARGET_TITLE.lower():
        reward = 1.0
    elif title and title.lower() != INITIAL_TITLE.lower():
        # Title was changed from the original placeholder but not to the
        # exact target — partial credit for being on the right track.
        reward = 0.4
    else:
        reward = 0.0

    # --- Over-action penalty: distractor doc titles must be unchanged. ---
    for doc_id, expected_title in DISTRACTORS.items():
        doc = documents.get(doc_id, {}) or {}
        if _norm(doc.get("title")).lower() != expected_title.lower():
            reward = min(reward, 0.3)

    reward = max(0.0, min(1.0, reward))
    print("REWARD: " + str(round(reward, 1)))


if __name__ == "__main__":
    main()
