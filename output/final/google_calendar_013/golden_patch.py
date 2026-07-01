"""
Golden Patch: Make the "Yoga Class" event repeat every week.
Task ID: google_calendar_013
Domain: mock_websites
Mock: google_calendar
Changes: Set evt_040.recurring = "weekly". Leave evt_041 (one-off makeup) untouched.
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
# Make the recurring "Yoga Class" (evt_040) repeat weekly.
# evt_041 is the one-off makeup session on a different day → must stay "none".
for event in state['events']:
    if event.get('id') == 'evt_040':
        event['recurring'] = 'weekly'

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
