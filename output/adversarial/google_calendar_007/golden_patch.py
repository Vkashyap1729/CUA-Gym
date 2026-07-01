"""
Golden Patch: Jump the calendar to today.
Task ID: google_calendar_007
Domain: mock_websites
Mock: google_calendar
Changes: Set currentDate to today. view and events unchanged.

NOTE on "today": the task was authored against a FIXED system 'today' of
2026-03-13 (see the ground-truth context). Clicking the calendar's "today"
button in that authored world lands currentDate on 2026-03-13. We therefore
set currentDate to this fixed date — NOT datetime.now(), which would resolve to
whatever wall-clock day the pipeline happens to run on and drift off the
expected month.
"""
import copy

import requests

# --- Config ---
BASE_URL = 'https://cua-gym-google-calendar.xlang.ai'

# "Today" = the fixed system date the task was authored against.
TODAY = '2026-03-13'

# Read sid from initial_setup.py
with open('/tmp/task_web_sid') as f:
    sid = f.read().strip()

# --- Fetch current initial state ---
go = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
state = copy.deepcopy(go['initial_state'])

# --- Apply ONLY the minimal changes the task requires ---
# Jump to today: only currentDate changes; view and events remain untouched.
state['currentDate'] = f'{TODAY}T00:00:00.000Z'

# --- Write ONLY current_state (preserve initial_state) ---
resp = requests.post(
    f'{BASE_URL}/post?sid={sid}',
    json={'action': 'set_current', 'state': state},
    timeout=30,
)
assert resp.status_code == 200, f'set_current failed: {resp.text}'
print(f'Golden state applied via set_current: sid={sid} today={TODAY}')

# --- Verify diff exists ---
go2 = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go2['state_diff'], 'state_diff is empty — golden state matches initial (no changes applied)'
assert go2['current_state']['currentDate'][:10] == TODAY, 'currentDate not updated to today'
print('Verified: state_diff is non-empty and currentDate == today')
