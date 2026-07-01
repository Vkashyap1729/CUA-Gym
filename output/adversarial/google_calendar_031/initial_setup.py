"""
Initial Setup: Clean up duplicate "Lunch with Sarah" events
Task ID: google_calendar_031
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
# Two identical "Lunch with Sarah" events (evt_210, evt_211) on 2026-03-20 12:00-13:00,
# plus an unrelated "Afternoon Walk" (evt_212) that must remain untouched.
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
    ],
    "events": [
        {
            "id": "evt_210",
            "calendarId": "c1",
            "title": "Lunch with Sarah",
            "start": "2026-03-20T12:00:00.000Z",
            "end": "2026-03-20T13:00:00.000Z",
            "allDay": False,
            "location": "Downtown Cafe",
            "description": "",
            "guests": [],
            "color": "#039BE5",
            "recurring": "none",
            "reminders": [],
            "meetLink": "",
            "status": "confirmed",
        },
        {
            "id": "evt_211",
            "calendarId": "c1",
            "title": "Lunch with Sarah",
            "start": "2026-03-20T12:00:00.000Z",
            "end": "2026-03-20T13:00:00.000Z",
            "allDay": False,
            "location": "Downtown Cafe",
            "description": "",
            "guests": [],
            "color": "#039BE5",
            "recurring": "none",
            "reminders": [],
            "meetLink": "",
            "status": "confirmed",
        },
        {
            "id": "evt_212",
            "calendarId": "c1",
            "title": "Afternoon Walk",
            "start": "2026-03-20T15:00:00.000Z",
            "end": "2026-03-20T15:30:00.000Z",
            "allDay": False,
            "location": "",
            "description": "",
            "guests": [],
            "color": "#039BE5",
            "recurring": "none",
            "reminders": [],
            "meetLink": "",
            "status": "confirmed",
        },
    ],
    "view": "day",
    "currentDate": "2026-03-20T00:00:00.000Z",
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
lunch = [e for e in go['initial_state']['events'] if e['title'] == 'Lunch with Sarah']
assert len(lunch) == 2, f'Expected 2 Lunch with Sarah events, got {len(lunch)}'
print('Verified: initial_state and current_state are set (2 duplicate lunches present)')


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
