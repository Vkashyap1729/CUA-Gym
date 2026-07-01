"""
Initial Setup: Delete the old 'Weekly deals' promo from inbox
Task ID: gmail_016
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
# Inbox has 3 emails:
#   email_1 — the target 'Weekly deals' promo (must be deleted/trashed)
#   email_2 — 'Weekly deals — LAST CHANCE' distractor (similar sender/subject, must remain)
#   email_3 — 'Standup notes' distractor (must remain)
# Task is NOT yet done: email_1 is in inbox (fresh reward = 0.0).
state = {
    "user": {"userId": "u1", "username": "Demo User", "email": "demo@example.com"},
    "emails": [
        {
            "id": "email_1",
            "threadId": "thread_1",
            "from": {"name": "ShopMart Deals", "email": "deals@shopmart.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Weekly deals",
            "body": "<p>Check out this week's deals at ShopMart. Save on your favorite items!</p>",
            "timestamp": "2026-06-24T08:00:00Z",
            "read": True,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "promotions",
            "folder": "inbox",
            "attachments": []
        },
        {
            "id": "email_2",
            "threadId": "thread_2",
            "from": {"name": "ShopMart Deals", "email": "deals@shopmart.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Weekly deals — LAST CHANCE",
            "body": "<p>Last chance to grab this week's deals before they expire tonight!</p>",
            "timestamp": "2026-06-28T09:15:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "promotions",
            "folder": "inbox",
            "attachments": []
        },
        {
            "id": "email_3",
            "threadId": "thread_3",
            "from": {"name": "Alice Smith", "email": "alice@company.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Standup notes",
            "body": "<p>Here are today's standup notes. Please review before the sync.</p>",
            "timestamp": "2026-06-30T10:00:00Z",
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
