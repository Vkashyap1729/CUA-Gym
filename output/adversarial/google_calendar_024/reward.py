#!/usr/bin/env python3
"""
Reward for task google_calendar_024.

Task: Delete the "Holidays" calendar (c4) entirely.

Scoring (progressive, 0.0-1.0):
  - The Holidays calendar (id c4 / name "Holidays") must be removed from the
    calendars array -> this is the core scored target.
  - Over-action penalty: the Personal (c1) and Work (c2) calendars must remain.

All criteria are exact state checks (no LLM judge needed).
Initial state (c4 still present) -> 0.0
Golden state (c4 removed, c1 & c2 intact) -> 1.0
"""

import json
import urllib.request

BASE_URL = 'https://cua-gym-google-calendar.xlang.ai'


def _read_sid():
    with open('/tmp/task_web_sid', 'r') as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + '/go?sid=' + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _is_holidays(cal):
    """A calendar counts as the Holidays calendar by id or by name."""
    cid = (cal.get('id') or '').strip()
    name = (cal.get('name') or '').strip().lower()
    return cid == 'c4' or name == 'holidays'


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)

    current_state = data.get('current_state', {}) or {}
    calendars = current_state.get('calendars', []) or []

    cal_ids = {(c.get('id') or '').strip() for c in calendars}
    holidays_present = any(_is_holidays(c) for c in calendars)

    # Gate the entire reward on the core task: the Holidays calendar removed.
    if holidays_present:
        return 0.0

    reward = 0.5  # core action: Holidays calendar removed

    # Over-action guard: required distractor calendars must remain untouched.
    if 'c1' in cal_ids:
        reward += 0.25
    if 'c2' in cal_ids:
        reward += 0.25

    return round(reward, 2)


if __name__ == '__main__':
    try:
        score = compute_reward()
    except Exception as e:
        print('ERROR computing reward: ' + repr(e))
        score = 0.0
    print('REWARD: ' + str(score))
