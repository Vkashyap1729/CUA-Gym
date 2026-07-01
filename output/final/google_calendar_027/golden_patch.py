"""
Golden Patch: Consolidate two morning workout slots
Task ID: google_calendar_027
Domain: mock_websites
Mock: google_calendar
Changes: delete 'Morning Run' (evt_170); set 'Gym' (evt_171) start to 06:00 (end unchanged).
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
# 1) Delete the "Morning Run" event (evt_170)
state['events'] = [e for e in state['events'] if e.get('id') != 'evt_170']

# 2) Extend "Gym" (evt_171) to start at 6 AM instead of 7 AM (end stays 08:00)
for e in state['events']:
    if e.get('id') == 'evt_171':
        e['start'] = '2026-03-16T06:00:00.000Z'

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
