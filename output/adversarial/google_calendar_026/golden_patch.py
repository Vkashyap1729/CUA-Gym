"""
Golden Patch: Move "Vendor Call" to Wednesday March 18 (same time) and add Eve as a guest.
Task ID: google_calendar_026
Domain: mock_websites
Mock: google_calendar
Changes: evt_160 start/end moved 2026-03-17 -> 2026-03-18 (14:00-15:00 preserved);
         evt_160 guests becomes ['frank@example.com', 'eve@example.com']. evt_161 untouched.
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
for evt in state['events']:
    if evt['id'] == 'evt_160':
        # Move Tuesday Mar 17 -> Wednesday Mar 18, keeping the same 14:00-15:00 time.
        evt['start'] = '2026-03-18T14:00:00.000Z'
        evt['end'] = '2026-03-18T15:00:00.000Z'
        # Keep Frank, add Eve.
        if 'eve@example.com' not in evt['guests']:
            evt['guests'].append('eve@example.com')

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
