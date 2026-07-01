"""
Golden Patch: Create a new calendar named "Side Projects" with the lavender color.
Task ID: google_calendar_010
Domain: mock_websites
Mock: google_calendar
Changes: Append a new calendar {name: "Side Projects", color: "#7986CB"} to calendars.
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
# Append the new "Side Projects" calendar with lavender color. The three
# existing calendars (c1, c2, c3) are untouched.
state['calendars'].append({
    'id': 'c_side_projects',
    'name': 'Side Projects',
    'color': '#7986CB',
    'visible': True,
    'userId': 'u1',
    'isDefault': False,
})

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
