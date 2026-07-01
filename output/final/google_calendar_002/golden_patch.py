"""
Golden Patch: Delete the "Lunch with Sarah" event from my calendar.
Task ID: google_calendar_002
Domain: mock_websites
Mock: google_calendar
Changes: Remove evt_002 ("Lunch with Sarah") from the events array; leave
         evt_001 and evt_003 untouched.
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
# Delete the "Lunch with Sarah" event (evt_002) by id. Touch nothing else.
before = len(state['events'])
state['events'] = [e for e in state['events'] if e.get('id') != 'evt_002']
assert len(state['events']) == before - 1, 'Expected exactly one event removed'
assert all(e['title'] != 'Lunch with Sarah' for e in state['events']), 'Target still present'
assert any(e['id'] == 'evt_001' for e in state['events']), 'evt_001 distractor missing'
assert any(e['id'] == 'evt_003' for e in state['events']), 'evt_003 distractor missing'

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
