"""
Initial Setup: Reschedule the "Quarterly Planning" meeting to next Monday, March 23rd
Task ID: google_calendar_016
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
# currentDate 2026-03-13. Quarterly Planning (evt_070) is currently on Mon 2026-03-16
# 13:00-15:00; the task is NOT yet done. Budget Review (evt_071) is a distractor.
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
            "id": "evt_070",
            "calendarId": "c2",
            "title": "Quarterly Planning",
            "start": "2026-03-16T13:00:00.000Z",
            "end": "2026-03-16T15:00:00.000Z",
            "allDay": False,
            "location": "Conference Room A",
            "description": "Plan goals and priorities for the next quarter.",
            "guests": ["alice@example.com", "bob@example.com"],
            "color": "#33B679",
            "recurring": "none",
            "reminders": [{"type": "popup", "minutes": 10}],
            "meetLink": "",
            "status": "confirmed",
        },
        {
            "id": "evt_071",
            "calendarId": "c2",
            "title": "Budget Review",
            "start": "2026-03-16T15:30:00.000Z",
            "end": "2026-03-16T16:30:00.000Z",
            "allDay": False,
            "location": "Conference Room A",
            "description": "Review Q1 budget figures.",
            "guests": ["charlie@example.com"],
            "color": "#33B679",
            "recurring": "none",
            "reminders": [{"type": "popup", "minutes": 10}],
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
