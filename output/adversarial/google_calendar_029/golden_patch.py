"""
Golden Patch: Reschedule "Board Meeting" earlier, move to Family calendar, recolor grape purple
Task ID: google_calendar_029
Domain: mock_websites
Mock: google_calendar
Changes: evt_190 start 15:00->14:00, end 16:30->15:30 (90 min preserved, -1h),
         calendarId c2->c3, color #33B679->#8E24AA. evt_191 untouched.
"""
import copy
import json

import requests

# --- Config ---
BASE_URL = 'https://cua-gym-google-calendar.xlang.ai'

# Read sid from initial_setup.py
with open('/tmp/task_web_sid') as f:
    sid = f.read().strip()

# --- Fetch current initial state ---
go = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
state = copy.deepcopy(go['initial_state'])

# --- Apply ONLY the minimal changes the task requires ---
for ev in state['events']:
    if ev['id'] == 'evt_190':
        ev['start'] = '2026-03-24T14:00:00.000Z'
        ev['end'] = '2026-03-24T15:30:00.000Z'
        ev['calendarId'] = 'c3'
        ev['color'] = '#8E24AA'

# --- Write ONLY current_state (preserve initial_state) ---
resp = requests.post(
    f'{BASE_URL}/post?sid={sid}',
    json={'action': 'set_current', 'state': state},
    timeout=30,
)
assert resp.status_code == 200, f'set_current failed: {resp.text}'
print(f'Golden state applied via set_current: sid={sid}')

# --- Verify diff exists ---
go2 = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go2['state_diff'], 'state_diff is empty — golden state matches initial (no changes applied)'
print(f'Verified: state_diff is non-empty')
