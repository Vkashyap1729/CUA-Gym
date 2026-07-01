"""
Golden Patch: Move "1:1 with Manager" meeting from 9 AM to 4 PM (same day, 1h).
Task ID: google_calendar_011
Domain: mock_websites
Mock: google_calendar
Changes: evt_020 start 09:00->16:00 and end 10:00->17:00 (same date, 1h preserved). evt_021 untouched.
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
for event in state['events']:
    if event['id'] == 'evt_020':
        event['start'] = '2026-03-17T16:00:00.000Z'
        event['end'] = '2026-03-17T17:00:00.000Z'
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
