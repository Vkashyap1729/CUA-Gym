#!/usr/bin/env python3
"""Reward for google_docs task: create a new document titled "Onboarding Checklist"
containing a heading "Onboarding" and a paragraph "Complete all items before day one."

Progressive scoring (exact state checks only; no LLM judge needed):
  0.40  exactly one new document, titled "Onboarding Checklist", ownerId user-1
  0.30  its content has an "Onboarding" heading (<h1..6>)
  0.30  its content has a paragraph "Complete all items before day one."
Over-action penalties:
  - pre-existing document doc-1 ("HR Policies") must be untouched
  - exactly ONE new document may be created (extra new docs are penalized)
Scores 0.0 on the initial (not-done) state and 1.0 on the fully-completed state.
"""

import re
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"


def read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        import json

        return json.loads(resp.read().decode("utf-8"))


def strip_tags(html):
    """Return lowercased visible text of an HTML fragment, whitespace-normalized."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def heading_texts(html):
    """Inner text of each <h1>..<h6> heading in the HTML content."""
    out = []
    for m in re.finditer(r"<h[1-6][^>]*>(.*?)</h[1-6]>", html or "", re.I | re.S):
        out.append(strip_tags(m.group(1)))
    return out


def paragraph_texts(html):
    """Inner text of each <p> paragraph in the HTML content."""
    out = []
    for m in re.finditer(r"<p[^>]*>(.*?)</p>", html or "", re.I | re.S):
        out.append(strip_tags(m.group(1)))
    return out


def main():
    sid = read_sid()
    data = fetch_state(sid)

    initial = data.get("initial_state", {}) or {}
    current = data.get("current_state", {}) or {}

    init_docs = initial.get("documents", {}) or {}
    cur_docs = current.get("documents", {}) or {}

    # Identify documents introduced by the task (present now, absent initially).
    new_ids = [doc_id for doc_id in cur_docs if doc_id not in init_docs]

    score = 0.0

    # --- Locate the target new document: titled "Onboarding Checklist", owned by user-1
    target = None
    for doc_id in new_ids:
        doc = cur_docs.get(doc_id, {}) or {}
        if (doc.get("title", "") or "").strip().lower() == "onboarding checklist":
            target = doc
            break

    # 0.40 — exactly one new document, correctly titled, owned by user-1
    if target is not None:
        title_ok = (target.get("title", "") or "").strip() == "Onboarding Checklist"
        owner_ok = target.get("ownerId") == "user-1"
        if title_ok and owner_ok:
            score += 0.40
        elif title_ok:
            # title right but wrong/missing owner — partial credit
            score += 0.25

        content = target.get("content", "") or ""

        # 0.30 — an "Onboarding" heading
        if any(h.strip() == "onboarding" for h in heading_texts(content)):
            score += 0.30
        elif any("onboarding" in h for h in heading_texts(content)):
            score += 0.15  # heading present but not exactly "Onboarding"

        # 0.30 — a paragraph "Complete all items before day one."
        target_para = "complete all items before day one"
        paras = paragraph_texts(content)
        if any(p.rstrip(".").strip() == target_para for p in paras):
            score += 0.30
        elif any(target_para in p for p in paras):
            score += 0.20  # phrase present in a paragraph but with extra text
        elif target_para in strip_tags(content):
            score += 0.10  # phrase somewhere in content but not a clean paragraph

    # --- Over-action penalties -------------------------------------------------

    # Pre-existing doc-1 ("HR Policies") must be untouched.
    if "doc-1" in init_docs:
        init_d1 = init_docs.get("doc-1", {}) or {}
        cur_d1 = cur_docs.get("doc-1")
        if cur_d1 is None:
            score -= 0.30  # deleted the distractor doc
        else:
            for field in ("title", "content", "ownerId"):
                if (init_d1.get(field) or "") != (cur_d1.get(field) or ""):
                    score -= 0.30
                    break

    # Exactly one new document should be created.
    if len(new_ids) > 1:
        score -= 0.20 * (len(new_ids) - 1)

    score = max(0.0, min(1.0, score))
    print("REWARD: {:.1f}".format(score))


if __name__ == "__main__":
    main()
