"""
Golden Patch: Add a "Dentist Appointment" event on March 18, 2026 2-3 PM
Task ID: google_calendar_001
Domain: mock_websites
Mock: google_calendar
Changes: Append one new event ("Dentist Appointment", 2026-03-18 14:00-15:00,
         default Personal calendar c1) to the events array. Existing events untouched.
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
# Append the new "Dentist Appointment" event on the default Personal calendar (c1).
new_event = {
    "id": f"evt_{uuid.uuid4().hex[:12]}",
    "calendarId": "c1",
    "title": "Dentist Appointment",
    "start": "2026-03-18T14:00:00.000Z",
    "end": "2026-03-18T15:00:00.000Z",
    "allDay": False,
    "location": "",
    "description": "",
    "guests": [],
    "color": "#039BE5",
    "recurring": "none",
    "reminders": [{"type": "popup", "minutes": 10}],
    "meetLink": "",
    "status": "confirmed",
}
state["events"].append(new_event)

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
