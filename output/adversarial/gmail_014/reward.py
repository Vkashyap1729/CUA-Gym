import json
import urllib.request

BASE_URL = 'https://cua-gym-gmail.xlang.ai'


def _read_sid():
    with open('/tmp/task_web_sid') as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + '/go?sid=' + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _email_by_id(emails, eid):
    for e in emails or []:
        if e.get('id') == eid:
            return e
    return None


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)
    current = data.get('current_state', {}) or {}
    emails = current.get('emails', []) or []

    # Task-introduced change: email_1 (unread recruiter mail) must become read.
    e1 = _email_by_id(emails, 'email_1')
    e2 = _email_by_id(emails, 'email_2')  # distractor: same sender, already read
    e3 = _email_by_id(emails, 'email_3')  # distractor: different sender, unread

    if e1 is None:
        return 0.0

    # Primary (and only positive) goal: the recruiter's unread email
    # (email_1) has been opened, i.e. read flipped false -> true.
    # On the initial state read is still false -> 0.0; on the golden
    # state read is true -> 1.0 (before penalties).
    score = 1.0 if e1.get('read') is True else 0.0

    # Over-action penalties: the two distractors must be untouched.
    # email_2 was already read (read:true) and must stay read:true.
    if e2 is not None and e2.get('read') is not True:
        score -= 0.5

    # email_3 (different sender) was unread and must stay read:false;
    # opening it is over-action.
    if e3 is not None and e3.get('read') is not False:
        score -= 0.5

    # Clamp to [0.0, 1.0].
    score = max(0.0, min(1.0, score))

    return round(score, 2)


if __name__ == '__main__':
    reward = compute_reward()
    print('REWARD: ' + str(reward))
