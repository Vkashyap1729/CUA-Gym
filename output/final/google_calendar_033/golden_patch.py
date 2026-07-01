"""
Golden Patch: Hide the Family calendar, switch to Agenda view, jump to April 1, 2026.
Task ID: google_calendar_033
Domain: mock_websites
Mock: google_calendar
Changes:
  - calendars c3 (Family) visible -> False (c1, c2 unchanged)
  - view -> "agenda"
  - currentDate -> 2026-04-01
  - events array unchanged
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
# 1) Hide the Family calendar (c3)
for cal in state['calendars']:
    if cal['id'] == 'c3':
        cal['visible'] = False

# 2) Switch to Agenda view
state['view'] = 'agenda'

# 3) Jump the calendar to April 1, 2026
state['currentDate'] = '2026-04-01T00:00:00.000Z'

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
print(f'Verified: state_diff is non-empty')
