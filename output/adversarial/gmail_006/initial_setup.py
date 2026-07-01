"""
Initial Setup: Reply to Priya's email about the design review (3pm Thursday slot)
Task ID: gmail_006
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
# Inbox contains Priya's design-review email (email_1, thread_1) plus two
# distractor emails from other senders. No reply to Priya exists yet in sent,
# and no drafts — so the task is NOT yet done and a fresh reward = 0.0.
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
            "from": {"name": "Priya Raman", "email": "priya@studio.design"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Design review scheduling",
            "body": "Hi,<br><br>I'd like to set up a design review this week. "
                    "Could you let me know if the 3pm slot on Thursday works "
                    "for you? Happy to adjust if needed.<br><br>Thanks,<br>Priya",
            "timestamp": "2026-06-29T10:00:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": ["l1"],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
        {
            "id": "email_2",
            "threadId": "thread_2",
            "from": {"name": "Marcus Lee", "email": "marcus@vendorhub.io"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Your monthly invoice is ready",
            "body": "Hello,<br><br>Your invoice for June is now available in "
                    "your account dashboard.<br><br>Best,<br>Marcus",
            "timestamp": "2026-06-28T15:20:00Z",
            "read": True,
            "starred": False,
            "important": False,
            "labels": ["l4"],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
        {
            "id": "email_3",
            "threadId": "thread_3",
            "from": {"name": "Weekly Digest", "email": "news@techweekly.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "This week in tech: 5 stories you missed",
            "body": "Here are the top stories from around the industry this week.",
            "timestamp": "2026-06-27T08:00:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "promotions",
            "folder": "inbox",
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
