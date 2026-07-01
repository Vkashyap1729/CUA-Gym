#!/usr/bin/env python3
"""Reward for: Star the document titled "Q3 Marketing Plan".

Scores ONLY the task-introduced change: documents[doc-1].starred false -> true.
Distractors (doc-2 starred stays true, doc-3 starred stays false) must be unchanged.

Design: this is a single-toggle task, so the primary signal is binary. The reward
is the primary credit minus an over-action penalty for any distractor whose
`starred` flag was altered. On the pristine initial state the target is not
starred, so the score is 0.0; on the golden state it is 1.0.
"""
import json
import urllib.request

BASE_URL = 'https://cua-gym-google-docs.xlang.ai'

TARGET_TITLE = 'Q3 Marketing Plan'


def main():
    with open('/tmp/task_web_sid') as f:
        sid = f.read().strip()

    with urllib.request.urlopen(BASE_URL + '/go?sid=' + sid, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    initial = data.get('initial_state', {}) or {}
    current = data.get('current_state', {}) or {}

    init_docs = initial.get('documents', {}) or {}
    cur_docs = current.get('documents', {}) or {}

    # Locate the target document by title (fall back to doc-1).
    target_id = None
    for doc_id, doc in cur_docs.items():
        if (doc or {}).get('title') == TARGET_TITLE:
            target_id = doc_id
            break
    if target_id is None:
        for doc_id, doc in init_docs.items():
            if (doc or {}).get('title') == TARGET_TITLE:
                target_id = doc_id
                break
    if target_id is None:
        target_id = 'doc-1'

    target = cur_docs.get(target_id, {}) or {}

    score = 0.0

    # --- Primary criterion (1.0): target document is now starred ---
    # Only counts as a task-introduced change if it was NOT starred initially.
    init_target_starred = (init_docs.get(target_id, {}) or {}).get('starred')
    if target.get('starred') is True and init_target_starred is not True:
        score = 1.0

    # --- Over-action penalty: any OTHER document's `starred` flag must be unchanged ---
    # Each altered distractor removes 0.5 of credit.
    for doc_id, init_doc in init_docs.items():
        if doc_id == target_id:
            continue
        init_starred = (init_doc or {}).get('starred')
        cur_starred = (cur_docs.get(doc_id, {}) or {}).get('starred')
        if cur_starred != init_starred:
            score -= 0.5

    score = max(0.0, min(1.0, score))
    print('REWARD: ' + str(round(score, 2)))


if __name__ == '__main__':
    main()
