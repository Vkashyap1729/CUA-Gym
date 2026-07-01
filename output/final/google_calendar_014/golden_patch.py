"""
Golden Patch: Change the color of my "Birthday Party" event to tomato red.
Task ID: google_calendar_014
Domain: mock_websites
Mock: google_calendar
Changes: Set evt_050 ("Birthday Party") color to tomato (#D50000). Leave
         evt_051 ("Dinner Reservation") at its original peacock color.
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
# Recolor "Birthday Party" (evt_050) to tomato red (#D50000). Touch nothing else.
for event in state['events']:
    if event.get('id') == 'evt_050':
        event['color'] = '#D50000'

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
