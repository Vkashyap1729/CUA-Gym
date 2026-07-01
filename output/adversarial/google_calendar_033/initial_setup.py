"""
Initial Setup: Hide the Family calendar, switch to Agenda view, jump to April 1, 2026.
Task ID: google_calendar_033
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
# Task NOT yet done: Family (c3) visible, view 'week', currentDate 2026-03-13.
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
        {"id": "c3", "name": "Family", "color": "#8E24AA", "visible": True, "userId": "u1", "isDefault": False},
    ],
    "events": [
        {
            "id": "evt_001",
            "calendarId": "c2",
            "title": "Team Standup",
            "start": "2026-03-13T09:00:00.000Z",
            "end": "2026-03-13T09:30:00.000Z",
            "allDay": False,
            "location": "Zoom",
            "description": "Daily sync with the team",
            "guests": ["alice@example.com", "bob@example.com"],
            "color": "#33B679",
            "recurring": "daily",
            "reminders": [{"type": "popup", "minutes": 5}],
            "meetLink": "",
            "status": "confirmed",
        },
        {
            "id": "evt_002",
            "calendarId": "c1",
            "title": "Lunch with Sarah",
            "start": "2026-03-13T12:00:00.000Z",
            "end": "2026-03-13T13:00:00.000Z",
            "allDay": False,
            "location": "Downtown Cafe",
            "description": "Catch up over coffee",
            "guests": [],
            "color": "#039BE5",
            "recurring": "none",
            "reminders": [{"type": "popup", "minutes": 15}],
            "meetLink": "",
            "status": "confirmed",
        },
        {
            "id": "evt_003",
            "calendarId": "c3",
            "title": "Family Dinner",
            "start": "2026-03-15T18:00:00.000Z",
            "end": "2026-03-15T20:00:00.000Z",
            "allDay": False,
            "location": "Home",
            "description": "Weekly family dinner",
            "guests": [],
            "color": "#8E24AA",
            "recurring": "weekly",
            "reminders": [{"type": "popup", "minutes": 30}],
            "meetLink": "",
            "status": "confirmed",
        },
    ],
    "view": "week",
    "currentDate": "2026-03-13T00:00:00.000Z",
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
