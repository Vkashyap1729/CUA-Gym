"""
Initial Setup: Make the "Yoga Class" event repeat every week.
Task ID: google_calendar_013
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
# Two distinct "Yoga Class" events, both non-recurring:
#   evt_040 — the regular weekly slot (Mon 2026-03-16), recurring "none"
#   evt_041 — a one-off makeup session on a different day (Thu 2026-03-19), recurring "none"
# Task is NOT yet done: evt_040.recurring == "none" → fresh reward = 0.0
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
            "id": "evt_040",
            "calendarId": "c1",
            "title": "Yoga Class",
            "start": "2026-03-16T07:00:00.000Z",
            "end": "2026-03-16T08:00:00.000Z",
            "allDay": False,
            "location": "Community Studio",
            "description": "Morning yoga session",
            "guests": [],
            "color": "#039BE5",
            "recurring": "none",
            "reminders": [{"type": "popup", "minutes": 10}],
            "meetLink": "",
            "status": "confirmed",
        },
        {
            "id": "evt_041",
            "calendarId": "c1",
            "title": "Yoga Class",
            "start": "2026-03-19T07:00:00.000Z",
            "end": "2026-03-19T08:00:00.000Z",
            "allDay": False,
            "location": "Community Studio",
            "description": "One-off makeup session",
            "guests": [],
            "color": "#039BE5",
            "recurring": "none",
            "reminders": [{"type": "popup", "minutes": 10}],
            "meetLink": "",
            "status": "confirmed",
        },
    ],
    "view": "week",
    "currentDate": "2026-03-16T00:00:00.000Z",
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
