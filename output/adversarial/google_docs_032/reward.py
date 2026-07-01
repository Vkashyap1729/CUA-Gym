import json
import urllib.request

BASE_URL = 'https://cua-gym-google-docs.xlang.ai'


def get_state():
    with open('/tmp/task_web_sid') as f:
        sid = f.read().strip()
    url = BASE_URL + '/go?sid=' + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode())


def find_doc(documents):
    # Prefer the canonical id; fall back to title match.
    doc = documents.get('doc-1')
    if doc:
        return doc
    for d in documents.values():
        if isinstance(d, dict) and d.get('title') == 'Vendor List':
            return d
    return None


def main():
    data = get_state()
    current = data.get('current_state') or {}
    documents = current.get('documents') or {}

    doc = find_doc(documents)
    if not doc:
        print('REWARD: 0.0')
        return

    shared = doc.get('sharedWith') or []
    perms = {}
    for entry in shared:
        if isinstance(entry, dict):
            perms[entry.get('userId')] = entry.get('permission')

    score = 0.0

    # Task-introduced change 1: Bob (user-3) downgraded editor -> viewer.
    # 0.0 on initial (Bob is editor), 0.5 once Bob is viewer.
    if perms.get('user-3') == 'viewer':
        score += 0.5

    # Task-introduced change 2: Carol (user-4) removed completely.
    # 0.0 on initial (Carol present), 0.5 once Carol's entry is gone.
    if 'user-4' not in perms:
        score += 0.5

    # Constraint: Alice (user-2) must remain editor (unchanged). Penalize if
    # her access was removed or altered (over-action on the untouched entry).
    if perms.get('user-2') != 'editor':
        score -= 0.5

    # Over-action: no share entries should appear for users other than the
    # three originally on the doc (user-2/3/4). Any newly added sharee is a bug.
    extra = set(perms.keys()) - {'user-2', 'user-3', 'user-4'}
    extra.discard(None)
    score -= 0.5 * len(extra)

    score = max(0.0, min(1.0, score))
    print('REWARD: {:.1f}'.format(score))


if __name__ == '__main__':
    main()
