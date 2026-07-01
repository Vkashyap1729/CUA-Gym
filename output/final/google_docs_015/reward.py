#!/usr/bin/env python3
"""Reward for: Add a comment on the "Architecture Overview" document asking
"Should we mention the caching layer here?"

Scores ONLY the task-introduced change: exactly one new Comment added to the
"Architecture Overview" document (doc-1), authored by user-1, resolved=false,
whose content is the question about the caching layer. Document content and all
other state must be unchanged (over-action penalty).
"""
import json
import urllib.request

BASE_URL = 'https://cua-gym-google-docs.xlang.ai'

TARGET_TITLE = 'Architecture Overview'
TARGET_DOC_ID = 'doc-1'
EXPECTED_AUTHOR = 'user-1'


def _read_sid():
    with open('/tmp/task_web_sid') as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + '/go?sid=' + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _find_doc_id(documents):
    """Locate the target document by title, falling back to the known id."""
    if not isinstance(documents, dict):
        return TARGET_DOC_ID
    for doc_id, doc in documents.items():
        if isinstance(doc, dict) and str(doc.get('title', '')).strip().lower() == TARGET_TITLE.lower():
            return doc_id
    return TARGET_DOC_ID


def main():
    sid = _read_sid()
    data = _fetch_state(sid)

    initial = data.get('initial_state', {}) or {}
    current = data.get('current_state', {}) or {}

    init_docs = initial.get('documents', {}) or {}
    cur_docs = current.get('documents', {}) or {}
    init_comments = initial.get('comments', []) or []
    cur_comments = current.get('comments', []) or []

    doc_id = _find_doc_id(cur_docs if cur_docs else init_docs)

    score = 0.0

    # --- Identify new comments (present now, absent initially) ---
    init_ids = {c.get('id') for c in init_comments if isinstance(c, dict)}
    new_comments = [
        c for c in cur_comments
        if isinstance(c, dict) and c.get('id') not in init_ids
    ]
    new_on_doc = [c for c in new_comments if c.get('docId') == doc_id]

    if not new_on_doc:
        print('No new comment found on the target document.')
        print('REWARD: 0.0')
        return

    # 0.25 — a new comment was added on the correct document
    score += 0.25

    # 0.15 — exactly one new comment on the doc, and no stray new comments elsewhere
    if len(new_on_doc) == 1 and len(new_comments) == 1:
        score += 0.15

    # Choose the candidate comment (the one on the target doc most likely to be the answer)
    target = new_on_doc[0]

    # 0.10 — authored by the current user
    if target.get('userId') == EXPECTED_AUTHOR:
        score += 0.10

    # 0.10 — comment is unresolved (open question)
    if target.get('resolved') is False:
        score += 0.10

    # 0.40 — content matches the intended question about the caching layer
    content = str(target.get('content', '')).strip()
    if content:
        from reward_judge import call_llm_judge
        # JUSTIFICATION: The comment wording is open-ended natural language, so an
        # exact string match is too brittle. We use the LLM judge ONLY to confirm
        # the comment semantically asks whether the caching layer should be
        # mentioned in the document. This subjective check is exactly 40% of the
        # score; all other criteria above are exact state checks.
        judge_score = call_llm_judge(
            task_instruction=(
                'Add a comment on the "Architecture Overview" document asking '
                '"Should we mention the caching layer here?"'
            ),
            success_criteria=(
                'The comment text must, in substance, ask/suggest whether the '
                'caching layer should be mentioned or included in the document. '
                'Minor wording differences are acceptable, but it must clearly be '
                'about the caching layer and be posed as a question or suggestion. '
                'Score 1.0 if it does, 0.0 if it is about something else.'
            ),
            state_excerpt='Comment text the user wrote:\n"""' + content + '"""',
        )
        try:
            score += 0.40 * float(judge_score)
        except (TypeError, ValueError):
            pass

    # --- Over-action penalty: document content / other docs must be unchanged ---
    over_action = False

    # Target document content must be unchanged
    init_doc = init_docs.get(doc_id, {}) if isinstance(init_docs, dict) else {}
    cur_doc = cur_docs.get(doc_id, {}) if isinstance(cur_docs, dict) else {}
    if init_doc.get('content') != cur_doc.get('content'):
        over_action = True
    if init_doc.get('title') != cur_doc.get('title'):
        over_action = True

    # No documents added or removed
    if set(init_docs.keys()) != set(cur_docs.keys()):
        over_action = True

    # Pre-existing comments must be untouched
    init_by_id = {c.get('id'): c for c in init_comments if isinstance(c, dict)}
    cur_by_id = {c.get('id'): c for c in cur_comments if isinstance(c, dict)}
    for cid, c in init_by_id.items():
        if cid not in cur_by_id or cur_by_id[cid] != c:
            over_action = True
            break

    if over_action:
        print('Over-action detected: unrelated state was modified; capping score.')
        score = min(score, 0.5)

    score = max(0.0, min(1.0, round(score, 2)))
    print('REWARD: ' + str(score))


if __name__ == '__main__':
    main()
