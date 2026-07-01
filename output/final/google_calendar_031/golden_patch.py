"""
Golden Patch: Clean up duplicate "Lunch with Sarah" events
Task ID: google_calendar_031
Domain: mock_websites
Mock: google_calendar
Changes: Remove one of the two identical "Lunch with Sarah" events (delete evt_211),
         leaving a single "Lunch with Sarah" and the unrelated "Afternoon Walk" intact.
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
# Delete the duplicate "Lunch with Sarah" (evt_211), keeping evt_210 and evt_212.
state['events'] = [e for e in state['events'] if e['id'] != 'evt_211']

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
lunch = [e for e in go2['current_state']['events'] if e['title'] == 'Lunch with Sarah']
assert len(lunch) == 1, f'Expected 1 Lunch with Sarah event after patch, got {len(lunch)}'
walk = [e for e in go2['current_state']['events'] if e['title'] == 'Afternoon Walk']
assert len(walk) == 1, 'Afternoon Walk event must remain intact'
print('Verified: state_diff is non-empty; exactly one Lunch remains, Afternoon Walk intact')
