"""Reward for: Share the "Launch Checklist" with Bob Smith and give him editor access.

Scores ONLY the task-introduced change: doc-1 "Launch Checklist" sharedWith must
gain {userId: user-3 (Bob Smith), permission: editor}, while the pre-existing
Alice (user-2) editor entry remains and no duplicate user-3 entries are created.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"

DOC_ID = "doc-1"
DOC_TITLE = "Launch Checklist"
TARGET_USER = "user-3"  # Bob Smith
TARGET_PERMISSION = "editor"
EXISTING_USER = "user-2"  # Alice Chen (pre-shared editor, must remain)


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_doc(documents):
    """Resolve the target document by ID, falling back to title match."""
    if isinstance(documents, dict):
        if DOC_ID in documents:
            return documents[DOC_ID]
        for doc in documents.values():
            if isinstance(doc, dict) and doc.get("title") == DOC_TITLE:
                return doc
    return None


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)
    current = data.get("current_state") or {}
    initial = data.get("initial_state") or {}

    documents = current.get("documents") or {}
    doc = _find_doc(documents)
    if not isinstance(doc, dict):
        return 0.0

    shared = doc.get("sharedWith")
    if not isinstance(shared, list):
        return 0.0

    # Entries (userId -> list of permissions) for the target doc.
    target_perms = [
        e.get("permission")
        for e in shared
        if isinstance(e, dict) and e.get("userId") == TARGET_USER
    ]
    existing_perms = [
        e.get("permission")
        for e in shared
        if isinstance(e, dict) and e.get("userId") == EXISTING_USER
    ]

    # The ONLY task-introduced change is adding Bob (user-3) as editor.
    # Initial state has NO user-3 entry, so it must score 0.0 here.
    if not target_perms:
        return 0.0

    score = 0.0

    # --- Bob Smith was added (any permission) — 0.5 ---
    score += 0.5

    # --- Bob Smith has exactly editor access, no duplicate entries — 0.5 ---
    bob_correct = len(target_perms) == 1 and target_perms[0] == TARGET_PERMISSION
    if bob_correct:
        score += 0.5

    # --- The pre-existing Alice editor entry must be preserved unchanged ---
    # Not awarded as independent credit (it exists in the initial state too);
    # instead, breaking it caps the score since it signals over-action.
    alice_ok = len(existing_perms) == 1 and existing_perms[0] == "editor"
    if not alice_ok:
        score = min(score, 0.5)

    # --- Over-action penalty: no OTHER document's sharing may change ---
    # Compare every document's sharedWith vs initial, except the target doc.
    init_docs = initial.get("documents") or {}
    if isinstance(init_docs, dict):
        for did, init_doc in init_docs.items():
            if did == DOC_ID:
                continue
            if not isinstance(init_doc, dict):
                continue
            cur_doc = documents.get(did) if isinstance(documents, dict) else None
            init_shared = init_doc.get("sharedWith")
            cur_shared = cur_doc.get("sharedWith") if isinstance(cur_doc, dict) else None
            if json.dumps(init_shared, sort_keys=True) != json.dumps(cur_shared, sort_keys=True):
                # A distractor document's sharing was altered — zero out.
                return 0.0

    return round(min(score, 1.0), 2)


if __name__ == "__main__":
    try:
        reward = compute_reward()
    except Exception:
        reward = 0.0
    print("REWARD: " + str(reward))
