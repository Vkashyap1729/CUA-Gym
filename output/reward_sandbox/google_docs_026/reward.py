#!/usr/bin/env python3
"""Reward for google_docs_026.

Task: In "Conference Agenda", correct the date from "March 5" to "March 12",
then resolve the comment that flagged the wrong date.

Scoring (progressive, 0.0-1.0), exact state checks only:
  - 0.6  documents[doc-1].content has "March 5" replaced with "March 12"
         (rest of the paragraph preserved: still contains "in Hall B")
  - 0.4  comment-1.resolved == true
Over-action guards: zero out if the doc title is altered or the comment
text/author is altered.
"""

import re
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        import json

        return json.loads(resp.read().decode("utf-8"))


def _strip_tags(html):
    """Remove HTML tags and collapse whitespace for robust text matching."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)
    current = data.get("current_state", {}) or {}

    documents = current.get("documents", {}) or {}
    comments = current.get("comments", []) or []

    # Locate the "Conference Agenda" document.
    doc = None
    for d in documents.values():
        if (d.get("title") or "").strip().lower() == "conference agenda":
            doc = d
            break
    if doc is None:
        # Fall back to the known id from the ground-truth context.
        doc = documents.get("doc-1")

    score = 0.0

    # ---- Over-action guard: title must remain "Conference Agenda".
    if doc is None or (doc.get("title") or "").strip().lower() != "conference agenda":
        print("REWARD: 0.0")
        return 0.0

    content_text = _strip_tags(doc.get("content", ""))

    # ---- Criterion 1 (0.6): date corrected March 5 -> March 12, rest preserved.
    has_new_date = re.search(r"\bmarch\s+12\b", content_text, re.IGNORECASE) is not None
    has_old_date = re.search(r"\bmarch\s+5\b", content_text, re.IGNORECASE) is not None
    rest_preserved = "in hall b" in content_text.lower()

    if has_new_date and not has_old_date and rest_preserved:
        score += 0.6
    elif has_new_date and not has_old_date:
        # Date fixed but surrounding text was clobbered: partial credit.
        score += 0.3

    # ---- Criterion 2 (0.4): the flagging comment is resolved.
    target_comment = None
    for c in comments:
        if c.get("id") == "comment-1":
            target_comment = c
            break
    if target_comment is None:
        # Fall back: the unresolved comment on this doc that flags the date.
        doc_id = doc.get("id")
        for c in comments:
            if c.get("docId") == doc_id and "march 12" in (c.get("content") or "").lower():
                target_comment = c
                break

    if target_comment is not None:
        # Over-action guard: the comment text/author must be unchanged.
        content_ok = "march 12" in (target_comment.get("content") or "").lower()
        author_ok = target_comment.get("userId") == "user-2"
        if target_comment.get("resolved") is True and content_ok and author_ok:
            score += 0.4

    score = round(score, 2)
    print("REWARD:", score)
    return score


if __name__ == "__main__":
    compute_reward()
