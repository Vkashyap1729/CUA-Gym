"""Reward for google_docs_033.

Task: Disable link sharing on "Confidential Memo" and remove the one external
collaborator so only the owner can access it.

Scoring (exact state checks only):
  - 0.5  linkSharing.enabled == False on the "Confidential Memo" document
  - 0.5  sharedWith is empty (the external collaborator removed)
Over-action guard: title and content of the target doc must be unchanged.
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


def _find_doc(documents, title):
    """Locate the target document by title (fall back to doc-1)."""
    for doc_id, doc in documents.items():
        if (doc.get("title") or "").strip().lower() == title.strip().lower():
            return doc
    return documents.get("doc-1")


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)

    current = data.get("current_state") or {}
    initial = data.get("initial_state") or {}

    cur_docs = current.get("documents") or {}
    init_docs = initial.get("documents") or {}

    doc = _find_doc(cur_docs, "Confidential Memo")
    if not doc:
        print("No 'Confidential Memo' document found in current state.")
        return 0.0

    init_doc = _find_doc(init_docs, "Confidential Memo") or {}

    score = 0.0

    # --- Criterion 1: link sharing disabled (0.5) ---
    link_sharing = doc.get("linkSharing") or {}
    if link_sharing.get("enabled") is False:
        score += 0.5
        print("[+0.5] linkSharing.enabled is False")
    else:
        print("[ +0 ] linkSharing.enabled is not False:", link_sharing.get("enabled"))

    # --- Criterion 2: external collaborator removed (0.5) ---
    shared_with = doc.get("sharedWith")
    if isinstance(shared_with, list) and len(shared_with) == 0:
        score += 0.5
        print("[+0.5] sharedWith is empty (collaborator removed)")
    else:
        print("[ +0 ] sharedWith not empty:", shared_with)

    # --- Over-action guard: title/content must be unchanged ---
    if init_doc:
        if doc.get("title") != init_doc.get("title"):
            print("[penalty] title changed; capping reward at 0.0")
            return 0.0
        if doc.get("content") != init_doc.get("content"):
            print("[penalty] content changed; capping reward at 0.0")
            return 0.0

    return round(score, 2)


if __name__ == "__main__":
    try:
        reward = compute_reward()
    except Exception as e:
        print("Error computing reward:", e)
        reward = 0.0
    print("REWARD: " + str(reward))
