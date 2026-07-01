#!/usr/bin/env python3
"""Reward for google_docs_018.

Task: Append a closing line "Prepared by the Operations team." as a NEW paragraph
at the end of the "Runbook" document (doc-1), preserving all existing content
(heading + both steps) in order.

Scoring is progressive (0.0-1.0) and credits ONLY the task-introduced change
(the appended closing paragraph). The unchanged baseline content earns no points,
so the not-done initial state scores 0.0. Destroying existing content or touching
other documents is penalized (over-action).
"""

import json
import re
import urllib.request

BASE_URL = 'https://cua-gym-google-docs.xlang.ai'

DOC_ID = 'doc-1'
TARGET = 'prepared by the operations team.'
HEADING = 'runbook'
STEP1 = 'step 1: restart the service.'
STEP2 = 'step 2: verify health checks.'


def get_sid():
    with open('/tmp/task_web_sid') as f:
        return f.read().strip()


def fetch_state(sid):
    url = BASE_URL + '/go?sid=' + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def strip_tags(s):
    return re.sub(r'<[^>]+>', '', s or '')


def norm(s):
    """Plain-text, whitespace-collapsed, lowercased."""
    txt = strip_tags(s)
    txt = txt.replace('&nbsp;', ' ').replace('&amp;', '&')
    return re.sub(r'\s+', ' ', txt).strip().lower()


def block_texts(content):
    """Ordered plain-text of each block-level element (h1-h6, p, li)."""
    matches = re.findall(
        r'<(h[1-6]|p|li)\b[^>]*>(.*?)</\1>',
        content or '',
        re.IGNORECASE | re.DOTALL,
    )
    return [norm(inner) for _tag, inner in matches]


def ordered_subsequence(blocks, needles):
    """True if every needle appears (substring) in blocks, in the given order."""
    i = 0
    for b in blocks:
        if i < len(needles) and needles[i] in b:
            i += 1
    return i == len(needles)


def main():
    sid = get_sid()
    data = fetch_state(sid)
    current = data.get('current_state', {}) or {}
    initial = data.get('initial_state', {}) or {}

    cur_docs = current.get('documents', {}) or {}
    init_docs = initial.get('documents', {}) or {}

    doc = cur_docs.get(DOC_ID, {}) or {}
    content = doc.get('content', '') or ''
    blocks = block_texts(content)
    full_text = norm(content)

    score = 0.0

    # --- Credit the task-introduced change: the appended closing paragraph ---

    # (a) The closing line text is present at all. (0.4)
    phrase_present = TARGET in full_text
    if phrase_present:
        score += 0.4

    # (b) It lives in its OWN distinct block (not merged into an existing line). (0.3)
    own_block = any(
        TARGET in b
        and STEP1 not in b
        and STEP2 not in b
        and HEADING not in b
        for b in blocks
    )
    if own_block:
        score += 0.3

    # (c) That block is APPENDED at the end (after Step 2 / is the last meaningful block). (0.3)
    appended_at_end = False
    if own_block:
        # find index of last block containing step2 and last block containing target
        step2_idx = max((i for i, b in enumerate(blocks) if STEP2 in b), default=-1)
        target_idx = max((i for i, b in enumerate(blocks) if TARGET in b), default=-1)
        non_empty = [i for i, b in enumerate(blocks) if b]
        is_last = bool(non_empty) and target_idx == non_empty[-1]
        if target_idx > step2_idx >= 0 and is_last:
            appended_at_end = True
    if appended_at_end:
        score += 0.3

    # --- Gate: existing content must be preserved in order (heading, step1, step2) ---
    preserved = ordered_subsequence(blocks, [HEADING, STEP1, STEP2])
    if not preserved and score > 0.0:
        # The required content was damaged while editing -> heavy penalty.
        score = min(score, 0.4)

    # --- Over-action penalty: no other document/comment should be touched ---
    over_action = False
    # new documents created
    if set(cur_docs.keys()) - set(init_docs.keys()):
        over_action = True
    # documents (other than doc-1) deleted or altered
    for did, idoc in init_docs.items():
        if did == DOC_ID:
            continue
        cdoc = cur_docs.get(did)
        if cdoc is None:
            over_action = True
            break
        for field in ('title', 'content', 'ownerId', 'starred', 'sharedWith', 'linkSharing'):
            if idoc.get(field) != cdoc.get(field):
                over_action = True
                break
        if over_action:
            break
    # comments touched
    if initial.get('comments') != current.get('comments'):
        over_action = True

    if over_action:
        score = max(0.0, score - 0.2)

    score = max(0.0, min(1.0, round(score, 2)))
    print('REWARD: {:.1f}'.format(score))


if __name__ == '__main__':
    main()
