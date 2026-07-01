"""
Golden Patch: Move the "Coffee Chat" event onto Work calendar instead of Personal
Task ID: google_calendar_019
Domain: mock_websites
Mock: google_calendar
Changes: evt_100 (Coffee Chat) calendarId c1 -> c2. evt_101 unchanged.
         Titles and times unchanged.
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
# Move "Coffee Chat" (evt_100) from Personal (c1) to Work (c2). Touch nothing else.
for ev in state['events']:
    if ev['id'] == 'evt_100':
        ev['calendarId'] = 'c2'

# --- Write ONLY current_state (preserve initial_state) ---
resp = requests.post(
    f'{BASE_URL}/post?sid={sid}',
    json={'action': 'set_current', 'state': state},
    timeout=30
)
assert resp.status_code == 200, f'set_current failed: {resp.text}'
print(f'Golden state applied via set_current: sid={sid}')

# --- Verify diff exists ---
go2 = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go2['state_diff'], 'state_diff is empty — golden state matches initial (no changes applied)'
print(f'Verified: state_diff is non-empty')
