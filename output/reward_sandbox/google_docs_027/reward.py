"""Reward for: Transfer access on "Shared Plan" from Bob to Alice.

Task: remove Bob's (user-3) access to doc-1 "Shared Plan" and instead share
with Alice (user-2) using the SAME editor permission Bob had.

Expected end state: documents[doc-1].sharedWith has exactly one entry,
{userId: user-2, permission: editor}; user-3 is gone.

Progressive score:
  +0.35  Bob (user-3) removed from sharedWith
  +0.35  Alice (user-2) present in sharedWith
  +0.20  Alice's permission is exactly "editor" (the permission Bob had)
  +0.10  sharedWith has exactly one entry (no leftover / extra shares)
Over-action guard: other documents' sharedWith must be untouched -> hard 0.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"
DOC_ID = "doc-1"
BOB = "user-3"
ALICE = "user-2"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _get_state():
    sid = _read_sid()
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _shared_with(state, doc_id):
    doc = (state.get("documents") or {}).get(doc_id) or {}
    return doc.get("sharedWith") or []


def main():
    data = _get_state()
    current = data.get("current_state") or {}
    initial = data.get("initial_state") or {}

    score = 0.0

    shared = _shared_with(current, DOC_ID)
    user_ids = [e.get("userId") for e in shared if isinstance(e, dict)]

    # --- Over-action guard: other documents must be untouched ---------------
    init_docs = initial.get("documents") or {}
    cur_docs = current.get("documents") or {}
    for did in init_docs:
        if did == DOC_ID:
            continue
        if _shared_with(initial, did) != _shared_with(current, did):
            print("Over-action: sharing on a distractor document changed:", did)
            print("REWARD: 0.0")
            return

    # --- Core criteria ------------------------------------------------------
    bob_present = BOB in user_ids
    if not bob_present:
        score += 0.35  # Bob's access removed

    alice_entries = [e for e in shared if isinstance(e, dict) and e.get("userId") == ALICE]
    if alice_entries:
        score += 0.35  # Alice now has access
        if alice_entries[0].get("permission") == "editor":
            score += 0.20  # same editor permission Bob had

    # Exactly one share entry (Alice as editor), nothing left over / extra
    if len(shared) == 1 and not bob_present and alice_entries:
        score += 0.10

    score = round(min(score, 1.0), 2)
    print("doc-1 sharedWith:", shared)
    print("REWARD:", score)


if __name__ == "__main__":
    main()
