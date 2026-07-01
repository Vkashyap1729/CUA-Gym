"""
Initial Setup: Apply 'Travel' label to the SkyJet flight confirmation email
Task ID: gmail_005
Domain: mock_websites
Mock: gmail
"""
import json
import os
import shlex
import subprocess
import time
import uuid

import requests

# --- Config ---
BASE_URL = 'https://cua-gym-gmail.xlang.ai'
sid = str(uuid.uuid4())

# Persist sid for golden_patch.py and reward.py
with open('/tmp/task_web_sid', 'w') as f:
    f.write(sid)

# --- Build initial state ---
# Task is NOT yet done: email_2 (the SkyJet flight confirmation) has NO labels.
# Distractors:
#   email_1 already has label l1 (Work) — must be preserved
#   email_3 is a hotel reservation (travel-related but NOT the flight) — stays unlabeled
#   email_4 unlabeled — stays unlabeled
state = {
    "user": {"userId": "u1", "username": "Demo User", "email": "demo@example.com"},
    "emails": [
        {
            "id": "email_1",
            "threadId": "thread_1",
            "from": {"name": "Alice Smith", "email": "alice@company.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Q4 Project Roadmap Update",
            "body": "Please review the attached roadmap before our sync.",
            "timestamp": "2026-02-09T11:30:00Z",
            "read": False,
            "starred": True,
            "important": True,
            "labels": ["l1"],
            "category": "primary",
            "folder": "inbox",
            "attachments": []
        },
        {
            "id": "email_2",
            "threadId": "thread_2",
            "from": {"name": "SkyJet Airlines", "email": "booking@skyjet.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Your flight to Denver is confirmed",
            "body": "Thank you for booking with SkyJet Airlines. Your flight to Denver (DEN) is confirmed. Confirmation code: SJ8842. Departure: 2026-03-14 08:20 AM.",
            "timestamp": "2026-02-10T09:05:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "primary",
            "folder": "inbox",
            "attachments": []
        },
        {
            "id": "email_3",
            "threadId": "thread_3",
            "from": {"name": "Grandview Hotel", "email": "reservations@grandviewhotel.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Reservation reminder",
            "body": "This is a friendly reminder about your upcoming stay at Grandview Hotel. Check-in: 2026-03-14.",
            "timestamp": "2026-02-11T14:20:00Z",
            "read": True,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "primary",
            "folder": "inbox",
            "attachments": []
        },
        {
            "id": "email_4",
            "threadId": "thread_4",
            "from": {"name": "Weekly Digest", "email": "news@digest.example.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Your weekly news digest",
            "body": "Here are the top stories from this week.",
            "timestamp": "2026-02-12T07:00:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "primary",
            "folder": "inbox",
            "attachments": []
        }
    ],
    "labels": [
        {"id": "l1", "name": "Work", "color": "#ef4444"},
        {"id": "l2", "name": "Personal", "color": "#3b82f6"},
        {"id": "l3", "name": "Travel", "color": "#22c55e"},
        {"id": "l4", "name": "Finance", "color": "#eab308"}
    ],
    "drafts": []
}

# --- Inject state ---
resp = requests.post(
    f'{BASE_URL}/post?sid={sid}',
    json={'action': 'set', 'state': state},
    timeout=30
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
