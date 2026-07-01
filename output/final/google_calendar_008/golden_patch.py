"""
Golden Patch: Collapse the left sidebar so the calendar takes the full width.
Task ID: google_calendar_008
Domain: mock_websites
Mock: google_calendar
Changes: set sidebarOpen from True to False. No other fields modified.
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
# Collapse the left sidebar.
state['sidebarOpen'] = False

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
assert go2['current_state'].get('sidebarOpen') is False, 'sidebarOpen should be False after patch'
assert go2['initial_state'].get('sidebarOpen') is True, 'initial_state must remain True'
print('Verified: state_diff is non-empty (sidebarOpen True -> False)')
