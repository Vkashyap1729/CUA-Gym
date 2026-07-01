import json
import urllib.request

BASE_URL = 'https://cua-gym-google-calendar.xlang.ai'


def _read_sid():
    with open('/tmp/task_web_sid') as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + '/go?sid=' + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _find(events, eid):
    for e in events:
        if e.get('id') == eid:
            return e
    return None


def _parse_dt(s):
    """Return (date, hour, minute) extracted from an ISO datetime string, or None."""
    if not isinstance(s, str) or 'T' not in s:
        return None
    try:
        date_part, time_part = s.split('T', 1)
        # strip trailing Z / fractional seconds / offset
        time_part = time_part.replace('Z', '')
        if '+' in time_part:
            time_part = time_part.split('+')[0]
        hh, mm = time_part.split(':')[0], time_part.split(':')[1]
        return (date_part, int(hh), int(mm))
    except Exception:
        return None


def main():
    sid = _read_sid()
    data = _fetch_state(sid)
    current = data.get('current_state', {}) or {}
    events = current.get('events', []) or []

    score = 0.0

    # --- Criterion 1: "Morning Run" (evt_170) deleted (0.5) ---
    run = _find(events, 'evt_170')
    if run is None:
        score += 0.5

    # --- Criterion 2: "Gym" (evt_171) extended to start at 06:00, end unchanged (08:00) (0.5) ---
    gym = _find(events, 'evt_171')
    if gym is not None:
        start = _parse_dt(gym.get('start', ''))
        end = _parse_dt(gym.get('end', ''))
        start_ok = start is not None and start[0] == '2026-03-16' and start[1] == 6 and start[2] == 0
        end_ok = end is not None and end[0] == '2026-03-16' and end[1] == 8 and end[2] == 0
        if start_ok and end_ok:
            score += 0.5
        elif start_ok:
            # partial: start moved correctly but end was altered
            score += 0.25

    # --- Over-action penalty: distractor "Breakfast Meeting" (evt_172) must be untouched ---
    breakfast = _find(events, 'evt_172')
    distractor_ok = True
    if breakfast is None:
        distractor_ok = False
    else:
        b_start = _parse_dt(breakfast.get('start', ''))
        b_end = _parse_dt(breakfast.get('end', ''))
        if not (b_start == ('2026-03-16', 9, 0) and b_end == ('2026-03-16', 10, 0)):
            distractor_ok = False
        if breakfast.get('title') != 'Breakfast Meeting' or breakfast.get('calendarId') != 'c2':
            distractor_ok = False

    if not distractor_ok:
        score = 0.0

    score = max(0.0, min(1.0, score))
    print('REWARD: ' + str(round(score, 2)))


if __name__ == '__main__':
    main()
