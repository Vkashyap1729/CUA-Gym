"""
Initial Setup: Forward Marcus's project brief to dana@corp.com (cc Marcus) and label original as Work
Task ID: gmail_011
Domain: mock_websites
Mock: gmail_mock

Initial state represents the task as NOT yet done:
  - email_1 (the brief from Marcus) has labels [] (not labeled Work)
  - no forwarded email exists in the "sent" folder
  - drafts is empty (no forward left unsent)
A correct reward evaluated on this state must therefore be 0.0.
"""
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
# The brief body is substantive so the forward's body can carry it verbatim.
BRIEF_BODY = (
    "<p>Hi team,</p>"
    "<p>Attached is the project brief for <b>Project Atlas</b>. "
    "The goal is to consolidate our three regional dashboards into a single "
    "unified analytics portal by end of Q3. Key milestones: design sign-off "
    "(week 2), backend integration (week 5), and beta launch (week 9). "
    "Please review the scope and flag any resourcing concerns.</p>"
    "<p>Best,<br/>Marcus</p>"
)

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
            "threadId": "thread_9",
            "from": {"name": "Marcus Lee", "email": "marcus@corp.com", "avatar": ""},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Project Atlas brief",
            "body": BRIEF_BODY,
            "timestamp": "2026-06-28T09:15:00Z",
            "read": True,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
        {
            # Distractor: same sender, personal subject — must NOT be forwarded or labeled.
            "id": "email_2",
            "threadId": "thread_10",
            "from": {"name": "Marcus Lee", "email": "marcus@corp.com", "avatar": ""},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Coffee?",
            "body": "<p>Hey, want to grab coffee this Friday afternoon? — Marcus</p>",
            "timestamp": "2026-06-27T16:40:00Z",
            "read": True,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
        {
            # Distractor: unrelated.
            "id": "email_3",
            "threadId": "thread_11",
            "from": {"name": "Priya Nair", "email": "priya@vendor.io", "avatar": ""},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Invoice #4821 for May services",
            "body": "<p>Please find attached invoice #4821 for services rendered in May.</p>",
            "timestamp": "2026-06-26T11:05:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
        {
            # Distractor: unrelated.
            "id": "email_4",
            "threadId": "thread_12",
            "from": {"name": "GitHub", "email": "noreply@github.com", "avatar": ""},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "[atlas-portal] CI build passed on main",
            "body": "<p>Your build #204 on branch main completed successfully.</p>",
            "timestamp": "2026-06-25T22:12:00Z",
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

# --- Inject state (creates BOTH initial_state and current_state) ---
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


# --- Launch browser (harmless no-op locally) ---
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
print('DONE')
