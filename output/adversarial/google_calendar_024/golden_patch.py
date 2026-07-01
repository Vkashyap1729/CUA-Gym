"""
Golden Patch: Delete the "Holidays" calendar entirely.
Task ID: google_calendar_024
Domain: mock_websites
Mock: google_calendar
Changes: Remove the Holidays calendar (c4) from the calendars array. Keep c1 and c2.
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
# Remove the Holidays calendar (c4). Touch nothing else (c1 Personal, c2 Work stay).
state['calendars'] = [c for c in state['calendars'] if c.get('id') != 'c4']

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
cal_ids = [c['id'] for c in go2['current_state']['calendars']]
assert 'c4' not in cal_ids, 'c4 still present in current state'
assert 'c1' in cal_ids and 'c2' in cal_ids, 'c1/c2 must remain'
print('Verified: state_diff is non-empty')
