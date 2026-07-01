"""
Golden Patch: Add a 30-minute popup reminder to the "Flight to Tokyo" event.
Task ID: google_calendar_015
Domain: mock_websites
Mock: google_calendar
Changes: Append {type: popup, minutes: 30} to evt_060.reminders. evt_061 untouched.
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
# Add a 30-minute popup reminder to evt_060 'Flight to Tokyo'.
for event in state['events']:
    if event['id'] == 'evt_060':
        event['reminders'].append({"type": "popup", "minutes": 30})
        break

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
print('Verified: state_diff is non-empty')
