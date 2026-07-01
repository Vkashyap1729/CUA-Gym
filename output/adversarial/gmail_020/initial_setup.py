"""
Initial Setup: Archive every inbox email from @newsletters.co, leave everything else.
Task ID: gmail_020
Domain: mock_websites
Mock: gmail_mock
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
# 5 emails, all in inbox. Task is NOT yet done (nothing archived).
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
            "from": {"name": "Newsletters Digest", "email": "digest@newsletters.co"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Monday digest",
            "body": "<p>Here is your Monday digest of top stories.</p>",
            "timestamp": "2026-06-29T08:00:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "promotions",
            "folder": "inbox",
            "attachments": [],
        },
        {
            "id": "email_2",
            "threadId": "thread_2",
            "from": {"name": "Product Weekly", "email": "weekly@newsletters.co"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Product weekly",
            "body": "<p>This week's product updates and highlights.</p>",
            "timestamp": "2026-06-28T09:15:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "promotions",
            "folder": "inbox",
            "attachments": [],
        },
        {
            # Distractor: domain is newsletters.co.uk, NOT newsletters.co — must stay in inbox.
            "id": "email_3",
            "threadId": "thread_3",
            "from": {"name": "Promo Team", "email": "promo@newsletters.co.uk"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Sale",
            "body": "<p>Big sale this weekend — don't miss out!</p>",
            "timestamp": "2026-06-27T10:30:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "promotions",
            "folder": "inbox",
            "attachments": [],
        },
        {
            # Distractor: different domain (company.com) — must stay in inbox.
            "id": "email_4",
            "threadId": "thread_4",
            "from": {"name": "Alice", "email": "alice@company.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Design review",
            "body": "<p>Can we schedule the design review for Thursday?</p>",
            "timestamp": "2026-06-26T14:45:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
        {
            "id": "email_5",
            "threadId": "thread_5",
            "from": {"name": "Community", "email": "bob@newsletters.co"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Community update",
            "body": "<p>Latest news from the community forum.</p>",
            "timestamp": "2026-06-25T16:20:00Z",
            "read": False,
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
print('DONE')
