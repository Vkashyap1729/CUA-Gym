#!/usr/bin/env python3
"""Reward for gmail task: Apply the Finance label to the invoice email from the vendor.

Task-introduced change (the ONLY thing scored):
  - email_1 (from bob@vendor.io, 'Invoice #2291 due') must gain the Finance label (l4),
    while retaining its existing Work label (l1) -> labels ['l1','l4'].
Distractors (must stay unchanged, else over-action penalty):
  - email_2 (Team lunch) labels stay []
  - email_3 (Statement ready) labels stay ['l4'] (already Finance)

Progressive, exact state checks only. 0.0 on initial (not-done), 1.0 on golden.
"""

import urllib.request
import json

BASE_URL = "https://cua-gym-gmail.xlang.ai"


def read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def emails_by_id(state):
    out = {}
    for e in (state or {}).get("emails", []) or []:
        out[e.get("id")] = e
    return out


def labels_of(email):
    if not email:
        return None
    return list(email.get("labels", []) or [])


def main():
    sid = read_sid()
    data = fetch_state(sid)
    current = data.get("current_state", {}) or {}

    by_id = emails_by_id(current)
    e1 = by_id.get("email_1")
    e2 = by_id.get("email_2")
    e3 = by_id.get("email_3")

    l1_labels = labels_of(e1)
    l2_labels = labels_of(e2)
    l3_labels = labels_of(e3)

    score = 0.0

    # --- Core action: Finance (l4) added to the vendor invoice email (email_1) ---
    # Gate everything on the core action so the initial (not-done) state scores 0.0.
    if l1_labels is not None and "l4" in l1_labels:
        score += 0.7  # Finance label applied to the correct email

        # Retain the pre-existing Work label (should not be removed).
        if "l1" in l1_labels:
            score += 0.1

        # --- Over-action penalties: distractor emails must be unchanged ---
        # email_2 (Team lunch) must remain with no labels.
        if l2_labels == []:
            score += 0.1
        # email_3 (Statement ready) already Finance; must remain exactly ['l4'].
        if l3_labels == ["l4"]:
            score += 0.1

    score = round(max(0.0, min(1.0, score)), 2)
    print("REWARD: {}".format(score))


if __name__ == "__main__":
    main()
