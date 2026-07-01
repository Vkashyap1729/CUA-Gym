import json
import urllib.request

BASE_URL = 'https://cua-gym-google-docs.xlang.ai'

# --- read session id -------------------------------------------------------
with open('/tmp/task_web_sid') as f:
    sid = f.read().strip()

# --- fetch state -----------------------------------------------------------
with urllib.request.urlopen(BASE_URL + '/go?sid=' + sid, timeout=30) as resp:
    data = json.loads(resp.read().decode('utf-8'))

current = data.get('current_state', {}) or {}
initial = data.get('initial_state', {}) or {}
documents = current.get('documents', {}) or {}
init_documents = initial.get('documents', {}) or {}


def find_doc(docs, title):
    """Locate a document by (case-insensitive) title; fall back to doc-1."""
    for doc_id, doc in docs.items():
        if (doc.get('title') or '').strip().lower() == title.strip().lower():
            return doc_id, doc
    if 'doc-1' in docs:
        return 'doc-1', docs['doc-1']
    return None, None


doc_id, doc = find_doc(documents, 'Salary Bands')

score = 0.0

if doc is None:
    print('Salary Bands document not found in current state.')
    print('REWARD: 0.0')
else:
    shared = doc.get('sharedWith', []) or []
    bob_present = any((e or {}).get('userId') == 'user-3' for e in shared)
    alice_entries = [e for e in shared if (e or {}).get('userId') == 'user-2']
    alice_viewer = any((e or {}).get('permission') == 'viewer' for e in alice_entries)

    # Core task: Bob (user-3) must be fully removed from sharedWith.
    if bob_present:
        # Not done — Bob still has access. Initial (not-done) state lands here.
        score = 0.0
        print('Bob (user-3) still present in sharedWith for "%s".' % doc.get('title'))
    else:
        # Bob removed -> main credit.
        score = 0.6
        print('Bob (user-3) removed from sharedWith. (+0.6)')

        # Alice (user-2) viewer entry must remain intact (no over-removal).
        if alice_viewer:
            score += 0.4
            print('Alice (user-2) viewer entry intact. (+0.4)')
        else:
            print('Alice (user-2) viewer entry missing/altered — over-action. (no +0.4)')

        # Over-action guard: sharedWith should end with exactly one entry.
        if len(shared) != 1:
            score = min(score, 0.5)
            print('sharedWith has %d entries (expected exactly 1) — '
                  'over-action penalty (cap 0.5).' % len(shared))

    # Distractor guard: other documents' sharedWith must be unchanged.
    for d_id, init_doc in init_documents.items():
        if d_id == doc_id:
            continue
        cur_doc = documents.get(d_id)
        if cur_doc is None:
            score = min(score, 0.5)
            print('Distractor document %s was deleted — over-action (cap 0.5).' % d_id)
            continue
        if (init_doc.get('sharedWith') or []) != (cur_doc.get('sharedWith') or []):
            score = min(score, 0.5)
            print('Distractor document %s sharing changed — over-action (cap 0.5).' % d_id)

    score = max(0.0, min(1.0, score))
    print('REWARD: %.1f' % score)
