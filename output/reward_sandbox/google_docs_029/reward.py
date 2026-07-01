"""Reward for google_docs task: add a comment quoting the "Recipes" heading.

Task: On the "Recipe Collection" document, add a comment that says
"Add prep time for each recipe" and quote the heading "Recipes" it refers to.

Expected end state: comments array gains exactly one Comment on doc-1 by user-1,
content ~ "Add prep time for each recipe", quotedText == "Recipes",
resolved == false. Document content unchanged.

Scoring (progressive, 0.0-1.0):
  0.25  exactly one NEW comment on doc-1 authored by user-1 (over-action penalty)
  0.25  quotedText == "Recipes"
  0.15  resolved == false
  0.35  content matches "Add prep time for each recipe" (LLM judge, subjective wording)
Gate: document content must be unchanged -> otherwise score is heavily penalized.
"""

import json
import urllib.request

BASE_URL = 'https://cua-gym-google-docs.xlang.ai'


def _read_sid():
    with open('/tmp/task_web_sid') as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + '/go?sid=' + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _norm(s):
    return ''.join((s or '').split()).lower()


def main():
    score = 0.0
    sid = _read_sid()
    data = _fetch_state(sid)

    initial = data.get('initial_state', {}) or {}
    current = data.get('current_state', {}) or {}

    init_comments = initial.get('comments', []) or []
    cur_comments = current.get('comments', []) or []

    # Identify NEW comments on doc-1 (not present in the initial state, by id).
    init_ids = {c.get('id') for c in init_comments}
    new_doc1_comments = [
        c for c in cur_comments
        if c.get('docId') == 'doc-1' and c.get('id') not in init_ids
    ]
    # New comments by the active user on doc-1.
    new_user1 = [c for c in new_doc1_comments if c.get('userId') == 'user-1']

    # --- Criterion 1: exactly one new comment on doc-1 by user-1 (0.25) ---
    # Penalize over-action: more than one added comment is not the requested change.
    if len(new_doc1_comments) == 1 and len(new_user1) == 1:
        score += 0.25
        target = new_user1[0]
    elif len(new_user1) >= 1:
        # A correct comment exists but extra distractor comments were also added.
        score += 0.10
        target = new_user1[0]
    else:
        target = None

    if target is not None:
        # --- Criterion 2: quotedText == "Recipes" (0.25) ---
        quoted = (target.get('quotedText') or '').strip()
        if quoted == 'Recipes':
            score += 0.25
        elif _norm(quoted) == _norm('Recipes'):
            score += 0.20

        # --- Criterion 3: resolved == false (0.15) ---
        if target.get('resolved') is False:
            score += 0.15

        # --- Criterion 4: content wording (0.35, LLM judge) ---
        content = (target.get('content') or '').strip()
        if content:
            if _norm(content) == _norm('Add prep time for each recipe'):
                # Exact-match fast path: no judge call needed.
                score += 0.35
            else:
                try:
                    from reward_judge import call_llm_judge

                    # JUSTIFICATION: comment wording is free-text; the agent may phrase
                    # "Add prep time for each recipe" with minor variation, so an LLM
                    # judge checks semantic equivalence rather than exact string match.
                    verdict = call_llm_judge(
                        'A user was asked to add a document comment that says '
                        '"Add prep time for each recipe". The comment they wrote is: '
                        '"' + content + '". Does this comment convey the same '
                        'instruction/meaning (asking to add preparation time for each '
                        'recipe)? Answer YES or NO.'
                    )
                    if isinstance(verdict, str) and 'yes' in verdict.lower():
                        score += 0.35
                except Exception:
                    pass

    # --- Gate: document content must be unchanged (over-action penalty) ---
    init_docs = initial.get('documents', {}) or {}
    cur_docs = current.get('documents', {}) or {}
    init_doc1 = init_docs.get('doc-1', {}) or {}
    cur_doc1 = cur_docs.get('doc-1', {}) or {}
    if init_doc1.get('content') != cur_doc1.get('content'):
        # Document body was modified -> task asked only for a comment.
        score = min(score, 0.3)

    # Penalize deletion/alteration of pre-existing comments (distractors).
    cur_by_id = {c.get('id'): c for c in cur_comments}
    for c in init_comments:
        cid = c.get('id')
        if cid not in cur_by_id or cur_by_id[cid] != c:
            score = min(score, 0.3)
            break

    score = max(0.0, min(1.0, round(score, 3)))
    print('REWARD: ' + str(score))


if __name__ == '__main__':
    main()
