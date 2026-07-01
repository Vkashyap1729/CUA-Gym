"""
Golden Patch: Reschedule the "Quarterly Planning" meeting to next Monday, March 23rd
Task ID: google_calendar_016
Domain: mock_websites
Mock: google_calendar
Changes: Move evt_070 (Quarterly Planning) from 2026-03-16 to 2026-03-23,
         keeping the same 13:00 start and 2-hour duration. evt_071 untouched.
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
# Reschedule "Quarterly Planning" (evt_070) to 2026-03-23, same 13:00 start, 2h duration.
for ev in state['events']:
    if ev['id'] == 'evt_070':
        ev['start'] = '2026-03-23T13:00:00.000Z'
        ev['end'] = '2026-03-23T15:00:00.000Z'
        break

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
