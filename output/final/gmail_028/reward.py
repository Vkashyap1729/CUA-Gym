#!/usr/bin/env python3
"""Reward for: Apply the 'Finance' label to the invoice email from the vendor.

Task-introduced change (the ONLY thing that earns credit):
  - email_1 (invoice #8823 from billing@acmevendor.com) gains label 'l4' (Finance).

Distractors / over-action (penalties only, never base credit):
  - email_2 (alice@company.com, Q3 planning) must keep exactly ['l1'].
  - email_3 (billing@acmevendor.com, Statement summary) must keep [].
  - No emails moved / read-flag toggled / deleted / created.

Credit is gated on the main change: if 'l4' is NOT on email_1 the score is 0.0.
This guarantees the initial (not-done) state scores 0.0 (distractors correct by
default earn nothing) and the golden state scores 1.0.
"""
import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"

FINANCE_LABEL = "l4"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _by_id(emails):
    return {e.get("id"): e for e in (emails or [])}


def main():
    sid = _read_sid()
    data = _fetch(sid)
    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}
    emails = _by_id(current.get("emails", []))
    init_emails = _by_id(initial.get("emails", []))

    e1 = emails.get("email_1", {})
    e2 = emails.get("email_2", {})
    e3 = emails.get("email_3", {})

    e1_labels = list(e1.get("labels", []) or [])
    e2_labels = list(e2.get("labels", []) or [])
    e3_labels = list(e3.get("labels", []) or [])

    # --- Main task: the invoice email (email_1) must have the Finance label. ---
    if FINANCE_LABEL not in e1_labels:
        print("Finance label (l4) on invoice email_1: NOT applied")
        print("REWARD: 0.0")
        return

    # Main change present -> full credit, minus over-action penalties.
    score = 1.0
    notes = []

    # email_1 started as [] -> should end as exactly ['l4'].
    extra_on_1 = [l for l in e1_labels if l != FINANCE_LABEL]
    if extra_on_1:
        score -= 0.3
        notes.append("email_1 gained unexpected labels %s" % extra_on_1)

    # email_2 must remain exactly ['l1'].
    if sorted(e2_labels) != ["l1"]:
        score -= 0.3
        notes.append("email_2 labels changed (expected ['l1'], got %s)" % e2_labels)

    # email_3 (same sender, not an invoice) must stay unlabeled.
    if e3_labels != []:
        score -= 0.3
        notes.append("email_3 labels changed (expected [], got %s)" % e3_labels)

    # No emails created or deleted.
    if set(emails.keys()) - set(init_emails.keys()):
        score -= 0.3
        notes.append("new emails created: %s" % sorted(set(emails.keys()) - set(init_emails.keys())))
    if set(init_emails.keys()) - set(emails.keys()):
        score -= 0.3
        notes.append("emails deleted: %s" % sorted(set(init_emails.keys()) - set(emails.keys())))

    # No email moved (folder) or read-flag toggled vs the initial state.
    for eid, ie in init_emails.items():
        ce = emails.get(eid)
        if ce is None:
            continue
        if ie.get("folder") != ce.get("folder"):
            score -= 0.3
            notes.append("%s moved %s -> %s" % (eid, ie.get("folder"), ce.get("folder")))
        if bool(ie.get("read", False)) != bool(ce.get("read", False)):
            score -= 0.2
            notes.append("%s read flag toggled" % eid)

    score = max(0.0, min(1.0, score))

    print("Finance label (l4) on invoice email_1: applied")
    for n in notes:
        print("Over-action penalty: %s" % n)
    if not notes:
        print("No over-action detected.")
    print("REWARD: %.1f" % score)


if __name__ == "__main__":
    main()
