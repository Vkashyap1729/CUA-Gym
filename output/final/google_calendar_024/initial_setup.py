"""
Initial Setup: Delete the "Holidays" calendar entirely.
Task ID: google_calendar_024
Domain: mock_websites
Mock: google_calendar
"""
import json
import os
import shlex
import subprocess
import time
import uuid

import requests

# --- Config ---
BASE_URL = 'https://cua-gym-google-calendar.xlang.ai'
sid = str(uuid.uuid4())

# Persist sid for golden_patch.py and reward.py
with open('/tmp/task_web_sid', 'w') as f:
    f.write(sid)

# --- Build initial state ---
# Calendars: c1 Personal, c2 Work, c4 Holidays (the target to be deleted).
# Events: evt_140 'National Holiday' on c4, evt_141 'Work Meeting' on c2.
# The Holidays calendar still PRESENT here => task not yet done => reward = 0.0.
state = {
    "user": {
        "id": "u1",
        "username": "Demo User",
        "email": "demo@example.com",
        "avatar": "https://picsum.photos/100/100?random=user1",
    },
    "calendars": [
        {"id": "c1", "name": "Personal", "color": "#039BE5", "visible": True, "userId": "u1", "isDefault": True},
        {"id": "c2", "name": "Work", "color": "#33B679", "visible": True, "userId": "u1", "isDefault": False},
        {"id": "c4", "name": "Holidays", "color": "#F4511E", "visible": True, "userId": "u1", "isDefault": False},
    ],
    "events": [
        {
            "id": "evt_140",
            "calendarId": "c4",
            "title": "National Holiday",
            "start": "2026-03-20T00:00:00.000Z",
            "end": "2026-03-21T00:00:00.000Z",
            "allDay": True,
            "location": "",
            "description": "Public holiday",
            "guests": [],
            "color": "#F4511E",
            "recurring": "none",
            "reminders": [],
            "meetLink": "",
            "status": "confirmed",
        },
        {
            "id": "evt_141",
            "calendarId": "c2",
            "title": "Work Meeting",
            "start": "2026-03-18T10:00:00.000Z",
            "end": "2026-03-18T11:00:00.000Z",
            "allDay": False,
            "location": "Conference Room A",
            "description": "Weekly project sync",
            "guests": ["alice@example.com", "bob@example.com"],
            "color": "#33B679",
            "recurring": "weekly",
            "reminders": [{"type": "popup", "minutes": 10}],
            "meetLink": "",
            "status": "confirmed",
        },
    ],
    "view": "week",
    "currentDate": "2026-03-18T00:00:00.000Z",
    "sidebarOpen": True,
    "settings": {
        "weekStart": 0,
        "defaultDuration": 60,
        "defaultView": "week",
        "defaultReminder": {"type": "popup", "minutes": 10},
        "timeFormat": "12h",
        "showWeekNumbers": False,
        "showDeclinedEvents": False,
    },
}

# --- Inject state ---
resp = requests.post(
    f'{BASE_URL}/post?sid={sid}',
    json={'action': 'set', 'state': state},
    timeout=30,
)
assert resp.status_code == 200, f'State injection failed: {resp.text}'
print(f'State injected: sid={sid}')

# --- Verify ---
go = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go['initial_state'] is not None, 'initial_state is None after injection'
cal_ids = [c['id'] for c in go['initial_state']['calendars']]
assert 'c4' in cal_ids, 'Holidays calendar (c4) missing from initial state'
print('Verified: initial_state and current_state are set')

# --- Launch browser ---
def launch_gui(command, delay_sec=1.0):
    env = os.environ.copy()
    env['DISPLAY'] = ':0'
    subprocess.Popen(
        shlex.split(command),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    time.sleep(delay_sec)

launch_gui(f'google-chrome "{BASE_URL}/?sid={sid}"', delay_sec=2.0)
print(f'GUI_READY: launched browser at {BASE_URL}/?sid={sid}')
