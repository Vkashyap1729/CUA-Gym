#!/usr/bin/env python3
"""Reward for google_docs_024.

Task: Share "Investor Deck Notes" with Alice as a commenter AND turn on link
sharing set to viewer, at the same time.

Two task-introduced changes on doc-1:
  1. sharedWith contains exactly {userId: user-2, permission: commenter}
  2. linkSharing.enabled == true with permission "viewer"

Scoring (progressive, exact state checks only):
  +0.5  Alice (user-2) shared as commenter (no extra/distractor share entries)
  +0.5  link sharing enabled with permission "viewer"
Initial state (sharedWith [], linkSharing.enabled false) -> 0.0
Fully completed state -> 1.0
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"
TARGET_TITLE = "Investor Deck Notes"
ALICE_ID = "user-2"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_doc(documents, title):
    for doc in documents.values():
        if isinstance(doc, dict) and doc.get("title") == title:
            return doc
    return None


def main():
    sid = _read_sid()
    data = _fetch_state(sid)
    current = data.get("current_state") or {}
    documents = current.get("documents") or {}

    score = 0.0

    doc = _find_doc(documents, TARGET_TITLE)
    if doc is None:
        print("Document '%s' not found." % TARGET_TITLE)
        print("REWARD: 0.0")
        return

    # ---- Criterion 1: shared with Alice as commenter, no extra entries ----
    shared = doc.get("sharedWith") or []
    alice_entries = [
        e for e in shared
        if isinstance(e, dict) and e.get("userId") == ALICE_ID
    ]
    other_entries = [
        e for e in shared
        if isinstance(e, dict) and e.get("userId") != ALICE_ID
    ]

    if len(alice_entries) == 1 and alice_entries[0].get("permission") == "commenter":
        if not other_entries:
            score += 0.5
            print("[+0.5] Alice (user-2) shared as commenter; no extra entries.")
        else:
            # Correct share present but over-action: distractor share entries added.
            score += 0.25
            print("[+0.25] Alice shared as commenter, but %d extra share entry(ies) "
                  "added (over-action penalty)." % len(other_entries))
    elif alice_entries:
        perm = alice_entries[0].get("permission")
        print("[+0.0] Alice shared but permission is '%s' (expected 'commenter')." % perm)
    else:
        print("[+0.0] Document not shared with Alice (user-2).")

    # ---- Criterion 2: link sharing enabled with permission viewer ----
    link = doc.get("linkSharing") or {}
    enabled = link.get("enabled")
    permission = link.get("permission")

    if enabled is True and permission == "viewer":
        score += 0.5
        print("[+0.5] Link sharing enabled with permission 'viewer'.")
    elif enabled is True:
        # Link sharing on but wrong permission.
        score += 0.25
        print("[+0.25] Link sharing enabled but permission is '%s' (expected 'viewer')."
              % permission)
    else:
        print("[+0.0] Link sharing not enabled.")

    score = round(min(score, 1.0), 2)
    print("REWARD: %s" % score)


if __name__ == "__main__":
    main()
