"""
Golden Patch: Create three back-to-back 30-min interview slots on the Work calendar
Task ID: google_calendar_028
Domain: mock_websites
Mock: google_calendar
Changes: Append three new events to calendar c2 (Work) on 2026-03-26:
         'Interview - Candidate A' 13:00-13:30,
         'Interview - Candidate B' 13:30-14:00,
         'Interview - Candidate C' 14:00-14:30.
         evt_180 (Lunch) is left untouched.
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
# Three back-to-back 30-minute interview slots on the Work calendar (c2).
interview_slots = [
    ("Interview - Candidate A", "2026-03-26T13:00:00.000Z", "2026-03-26T13:30:00.000Z"),
    ("Interview - Candidate B", "2026-03-26T13:30:00.000Z", "2026-03-26T14:00:00.000Z"),
    ("Interview - Candidate C", "2026-03-26T14:00:00.000Z", "2026-03-26T14:30:00.000Z"),
]

for idx, (title, start, end) in enumerate(interview_slots, start=1):
    state['events'].append({
        "id": f"evt_interview_{idx}",
        "calendarId": "c2",
        "title": title,
        "start": start,
        "end": end,
        "allDay": False,
        "location": "",
        "description": "",
        "guests": [],
        "color": "#33B679",
        "recurring": "none",
        "reminders": [{"type": "popup", "minutes": 10}],
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
print('DONE')
