import json
import urllib.request

BASE_URL = 'https://cua-gym-google-docs.xlang.ai'


def read_sid():
    with open('/tmp/task_web_sid') as f:
        return f.read().strip()


def fetch_state(sid):
    url = BASE_URL + '/go?sid=' + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def main():
    sid = read_sid()
    data = fetch_state(sid)
    current = data.get('current_state', {}) or {}
    documents = current.get('documents', {}) or {}

    doc1 = documents.get('doc-1', {}) or {}
    doc2 = documents.get('doc-2', {}) or {}
    doc3 = documents.get('doc-3', {}) or {}

    # Task: star both "Q1 OKRs" (doc-1) and "Q2 OKRs" (doc-2).
    # doc-3 "Q3 OKRs" is a distractor and must remain unstarred.
    score = 0.0

    # 0.5 for each correctly starred quarterly-goal doc.
    if doc1.get('starred') is True:
        score += 0.5
    if doc2.get('starred') is True:
        score += 0.5

    # Over-action penalty: starring the distractor doc-3 forfeits all credit.
    if doc3.get('starred') is True:
        score = 0.0

    score = max(0.0, min(1.0, score))
    print('REWARD: {:.1f}'.format(score))


if __name__ == '__main__':
    main()
