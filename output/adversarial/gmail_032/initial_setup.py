"""
Initial Setup: Save a draft email to the finance team reminding them the expense report is due Friday.
Task ID: gmail_032
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
# Task is NOT yet done: drafts is empty, no 'sent' email exists.
# Inbox has one unrelated email (email_1) that must remain untouched.
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
            "from": {"name": "Operations", "email": "ops@company.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "System status",
            "body": "All systems are currently operational. No action required.",
            "timestamp": "2026-06-29T09:15:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        }
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
