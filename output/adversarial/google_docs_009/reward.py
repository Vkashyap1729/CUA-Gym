"""Reward for: Turn on link sharing for "Customer FAQ" so anyone with the link can view it.

Task-introduced change: documents[doc "Customer FAQ"].linkSharing.enabled  false -> true
(permission must stay "viewer"). The distractor doc "Internal Wiki" must keep link
sharing disabled.

IMPORTANT: every credit is gated behind the core change (enabled -> true). Conditions
that are ALREADY true in the not-done initial state (permission == "viewer", and the
distractor "Internal Wiki" being disabled) earn NO standalone credit -- they only act
as multiplier / penalty once the core change has been made. This keeps the initial
state at exactly 0.0 and the completed golden state at 1.0.
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
    """documents is a map keyed by doc ID -> Document object."""
    if not isinstance(documents, dict):
        return None
    target = title.strip().lower()
    for doc in documents.values():
        if isinstance(doc, dict) and str(doc.get("title", "")).strip().lower() == target:
            return doc
    return None


def main():
    sid = _read_sid()
    data = _get_state(sid)
    current = data.get("current_state", {}) or {}
    documents = current.get("documents", {}) or {}

    target = _find_doc_by_title(documents, "Customer FAQ")
    if target is None:
        print("REWARD:", 0.0)
        return

    link = target.get("linkSharing", {}) or {}

    # --- Core task-introduced change: link sharing must be turned ON ---
    if link.get("enabled") is not True:
        # Not done. Nothing else can earn credit (all other conditions are
        # already satisfied in the initial state).
        print("REWARD:", 0.0)
        return

    score = 0.8  # core change accomplished

    # Permission must remain "viewer" (anyone with the link can VIEW, not edit).
    if str(link.get("permission", "")).strip().lower() == "viewer":
        score += 0.2
    # else: link sharing enabled but over-broad permission -> capped at 0.8

    # --- Over-action penalty: distractor "Internal Wiki" must stay disabled ---
    distractor = _find_doc_by_title(documents, "Internal Wiki")
    if distractor is not None:
        d_link = distractor.get("linkSharing", {}) or {}
        if d_link.get("enabled") is True:
            score -= 0.5  # touched the wrong document

    score = round(max(0.0, min(1.0, score)), 2)
    print("REWARD:", score)


if __name__ == "__main__":
    main()
