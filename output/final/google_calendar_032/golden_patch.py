"""
Golden Patch: Add "Mom's Birthday Dinner" event on Family calendar
Task ID: google_calendar_032
Domain: mock_websites
Mock: google_calendar
Changes: Append one new event (Mom's Birthday Dinner, c3 Family,
         2026-03-28 19:00-21:00, guest mom@example.com, 1-day-before popup
         reminder). evt_220 left untouched.
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
# Append the new "Mom's Birthday Dinner" event on the Family calendar (c3).
# evt_220 (Work Deadline) is left untouched and stays on c2.
state['events'].append({
    "id": "evt_moms_birthday_dinner",
    "calendarId": "c3",
    "title": "Mom's Birthday Dinner",
    "start": "2026-03-28T19:00:00.000Z",
    "end": "2026-03-28T21:00:00.000Z",
    "allDay": False,
    "location": "",
    "description": "",
    "guests": ["mom@example.com"],
    "color": "#8E24AA",
    "recurring": "none",
    "reminders": [{"type": "popup", "minutes": 1440}],
    "meetLink": "",
    "status": "confirmed",
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
