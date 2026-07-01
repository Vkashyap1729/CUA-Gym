"""
Golden Patch: Create an all-day event titled "Company Offsite" on March 27, 2026 on the Work calendar.
Task ID: google_calendar_017
Domain: mock_websites
Mock: google_calendar
Changes: Append one new all-day event 'Company Offsite' (calendarId c2/Work) spanning 2026-03-27.
"""
import copy
import json
import uuid

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
# Append a new all-day event on the Work calendar (c2). The existing Standup remains untouched.
state['events'].append({
    "id": f"evt_{uuid.uuid4().hex[:8]}",
    "calendarId": "c2",
    "title": "Company Offsite",
    "start": "2026-03-27T00:00:00.000Z",
    "end": "2026-03-28T00:00:00.000Z",
    "allDay": True,
    "location": "",
    "description": "",
    "guests": [],
    "color": "#33B679",
    "recurring": "none",
    "reminders": [],
    "meetLink": "",
    "status": "confirmed",
})

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
print('Verified: state_diff is non-empty')
