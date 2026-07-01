"""
Initial Setup: Empty spam — permanently delete every email in the spam folder.
Task ID: gmail_010
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
# inbox: 3 legitimate distractor emails (must remain untouched)
# spam: exactly 2 spam emails (email_5, email_6) to be permanently deleted
# trash: empty
state = {
    "user": {
        "userId": "u1",
        "username": "Demo User",
        "email": "demo@example.com",
    },
    "emails": [
        {
            "id": "email_1",
            "threadId": "thread_1",
            "from": {"name": "Alice Smith", "email": "alice@company.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Q4 Project Roadmap Update",
            "body": "<p>Please review the attached roadmap before Friday's meeting.</p>",
            "timestamp": "2026-06-28T11:30:00Z",
            "read": False,
            "starred": True,
            "important": True,
            "labels": ["l1"],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
        {
            "id": "email_2",
            "threadId": "thread_2",
            "from": {"name": "Bob Johnson", "email": "bob@partner.org"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Lunch next week?",
            "body": "<p>Are you free for lunch on Tuesday? Let me know.</p>",
            "timestamp": "2026-06-27T09:15:00Z",
            "read": True,
            "starred": False,
            "important": False,
            "labels": ["l2"],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
        {
            "id": "email_3",
            "threadId": "thread_3",
            "from": {"name": "Travel Desk", "email": "trips@travelco.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Your flight itinerary confirmation",
            "body": "<p>Your booking for the July trip is confirmed. See details inside.</p>",
            "timestamp": "2026-06-25T16:45:00Z",
            "read": True,
            "starred": False,
            "important": False,
            "labels": ["l3"],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
        {
            "id": "email_5",
            "threadId": "thread_5",
            "from": {"name": "Prize Notify", "email": "win@luckydraw.info"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "You won a $1000 gift card",
            "body": "<p>Congratulations! Click here to claim your $1000 gift card now!</p>",
            "timestamp": "2026-06-24T03:12:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "promotions",
            "folder": "spam",
            "attachments": [],
        },
        {
            "id": "email_6",
            "threadId": "thread_6",
            "from": {"name": "Crypto Alerts", "email": "promo@coinblast.biz"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Double your investment",
            "body": "<p>Guaranteed returns! Double your crypto investment in 24 hours.</p>",
            "timestamp": "2026-06-23T22:40:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "promotions",
            "folder": "spam",
            "attachments": [],
        },
    ],
    "labels": [
        {"id": "l1", "name": "Work", "color": "#ef4444"},
        {"id": "l2", "name": "Personal", "color": "#3b82f6"},
        {"id": "l3", "name": "Travel", "color": "#22c55e"},
        {"id": "l4", "name": "Finance", "color": "#eab308"},
    ],
    "drafts": [],
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
spam = [e for e in go['initial_state']['emails'] if e['folder'] == 'spam']
assert len(spam) == 2, f'Expected 2 spam emails, got {len(spam)}'
print('Verified: initial_state and current_state are set (2 spam emails present)')

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
