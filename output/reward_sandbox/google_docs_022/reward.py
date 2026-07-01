"""Reward for: lower link-sharing permission on "Public Roadmap" from editor to commenter.

Task-introduced change (the ONLY thing scored):
    documents[doc-1].linkSharing.permission : "editor" -> "commenter"
    documents[doc-1].linkSharing.enabled    : stays true

Scoring (progressive 0.0 - 1.0):
    0.5  the target doc's link sharing is still ENABLED (not accidentally turned off)
    0.5  the link sharing permission is exactly "commenter"
Over-action penalty: if any OTHER document's linkSharing changed, score is zeroed.

Initial state (permission == "editor") -> 0.0
Golden state  (permission == "commenter", enabled true) -> 1.0
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


def _find_target_doc(documents):
    """Locate the 'Public Roadmap' document. Prefer title match, fall back to doc-1."""
    for doc_id, doc in documents.items():
        if isinstance(doc, dict) and doc.get("title") == "Public Roadmap":
            return doc_id, doc
    if "doc-1" in documents:
        return "doc-1", documents["doc-1"]
    return None, None


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)

    current = data.get("current_state") or {}
    initial = data.get("initial_state") or {}
    cur_docs = current.get("documents") or {}
    init_docs = initial.get("documents") or {}

    target_id, target_doc = _find_target_doc(cur_docs)
    if target_doc is None:
        print("Target document 'Public Roadmap' not found in current state.")
        return 0.0

    link = target_doc.get("linkSharing") or {}
    enabled = link.get("enabled")
    permission = link.get("permission")
    print("Target doc:", target_id, "linkSharing:", link)

    # Over-action guard: no OTHER document's linkSharing may change.
    for doc_id, init_doc in init_docs.items():
        if doc_id == target_id:
            continue
        cur_doc = cur_docs.get(doc_id)
        if not isinstance(cur_doc, dict) or not isinstance(init_doc, dict):
            continue
        if (cur_doc.get("linkSharing") or {}) != (init_doc.get("linkSharing") or {}):
            print("Over-action: linkSharing changed on non-target doc", doc_id)
            return 0.0

    score = 0.0

    # 0.5 — link sharing must remain enabled (task says "people should comment").
    if enabled is True:
        score += 0.5
    else:
        print("linkSharing.enabled is not True:", enabled)

    # 0.5 — permission lowered to exactly "commenter".
    if permission == "commenter":
        score += 0.5
    else:
        print("linkSharing.permission is not 'commenter':", permission)

    # Initial state has permission == "editor" -> only the 0.5 enabled credit,
    # which would leave 0.5. Guard so the un-done initial state scores 0.0.
    if permission == "editor":
        print("Permission still 'editor' (initial / not-done state).")
        return 0.0

    return round(score, 2)


if __name__ == "__main__":
    try:
        reward = compute_reward()
    except Exception as exc:  # noqa: BLE001
        print("Error computing reward:", exc)
        reward = 0.0
    print("REWARD:", reward)
