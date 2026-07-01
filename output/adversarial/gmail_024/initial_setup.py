"""
Initial Setup: Recover accidentally-trashed client email to inbox (unread, starred),
then permanently delete the phishing email still in trash.
Task ID: gmail_024
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
# Trash has 2 emails: email_1 (client, trashed by mistake) and email_2 (phishing).
# Inbox has email_3 (distractor). Task is NOT yet done in this state:
#   email_1 is in trash, read=True, starred=False; email_2 still present.
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
            "from": {"name": "BigCo Client", "email": "client@bigco.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Contract signed — next steps",
            "body": "<p>Hi, we've signed the contract. Here are the next steps to kick off the project. Looking forward to working together.</p>",
            "timestamp": "2026-06-28T09:15:00Z",
            "read": True,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "primary",
            "folder": "trash",
            "attachments": [],
        },
        {
            "id": "email_2",
            "threadId": "thread_2",
            "from": {"name": "PayPal Security", "email": "security@paypa1-verify.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Verify your account NOW",
            "body": "<p>Your account has been limited. Click here immediately to verify your account or it will be suspended.</p>",
            "timestamp": "2026-06-29T03:42:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "primary",
            "folder": "trash",
            "attachments": [],
        },
        {
            "id": "email_3",
            "threadId": "thread_3",
            "from": {"name": "Alice Smith", "email": "alice@company.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "FYI",
            "body": "<p>Just wanted to keep you in the loop on the latest updates.</p>",
            "timestamp": "2026-06-30T14:05:00Z",
            "read": True,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "primary",
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
