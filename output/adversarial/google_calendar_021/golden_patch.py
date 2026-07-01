"""
Golden Patch: Extend the "Workshop" event so it ends at 5 PM instead of 3 PM.
Task ID: google_calendar_021
Domain: mock_websites
Mock: google_calendar
Changes: evt_120 ('Workshop') end changed from 15:00 to 17:00 (start unchanged).
         evt_121 ('Wrap-up Call') left untouched despite the new overlap.
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

# --- Apply ONLY the minimal change the task requires ---
# Extend Workshop (evt_120) to end at 5 PM. Start stays at 13:00.
for evt in state['events']:
    if evt['id'] == 'evt_120':
        evt['end'] = '2026-03-24T17:00:00.000Z'
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
print('Verified: state_diff is non-empty')
