"""
Initial Setup: Reorganize two flagged project emails (labels + star)
Task ID: gmail_034
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
# INITIAL (task NOT yet done):
#   labels: l1 Work (red), l2 Personal (blue)
#   email_1 (lead@company.com): labels ['l2'], starred False
#   email_2 (dev@company.com):  labels ['l2'], starred False
#   email_3 (friend@personal.com, distractor): labels ['l2'], starred False
state = {
    "user": {
        "userId": "u1",
        "username": "Demo User",
        "email": "demo@example.com",
        "avatar": "",
    },
    "emails": [
        {
            "id": "email_1",
            "threadId": "thread_1",
            "from": {"name": "Project Lead", "email": "lead@company.com", "avatar": ""},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Project Atlas milestone",
            "body": "<p>The next Project Atlas milestone is approaching. Please review the plan.</p>",
            "timestamp": "2026-02-09T09:15:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": ["l2"],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
        {
            "id": "email_2",
            "threadId": "thread_2",
            "from": {"name": "Dev Team", "email": "dev@company.com", "avatar": ""},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Project Atlas code freeze",
            "body": "<p>Reminder: the Project Atlas code freeze begins this Friday.</p>",
            "timestamp": "2026-02-09T10:05:00Z",
            "read": False,
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
            "from": {"name": "Friend", "email": "friend@personal.com", "avatar": ""},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Weekend plans",
            "body": "<p>Are you free this weekend? Let's grab lunch.</p>",
            "timestamp": "2026-02-09T11:00:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": ["l2"],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
    ],
    "labels": [
        {"id": "l1", "name": "Work", "color": "#ef4444"},
        {"id": "l2", "name": "Personal", "color": "#3b82f6"},
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
