"""
Golden Patch: Rename the event titled "Team Standup" to "Daily Engineering Sync".
Task ID: google_calendar_004
Domain: mock_websites
Mock: google_calendar
Changes: evt_001.title -> "Daily Engineering Sync"; all other fields of evt_001
         and all of evt_002 left untouched.
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
# Rename the event titled "Team Standup" to "Daily Engineering Sync".
for ev in state['events']:
    if ev.get('title') == 'Team Standup':
        ev['title'] = 'Daily Engineering Sync'

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
