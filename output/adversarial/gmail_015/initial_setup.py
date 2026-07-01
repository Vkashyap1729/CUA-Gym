"""
Initial Setup: Move the crypto-lottery junk email to spam
Task ID: gmail_015
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
# Inbox has 3 emails; task is NOT yet done (crypto-lottery email still in inbox).
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
            "from": {"name": "Crypto Lottery", "email": "prize@crypto-lottery-win.biz"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "You WON 5 BTC — claim now",
            "body": "<p>Congratulations! You have WON 5 BTC in the crypto lottery. Click here to claim your prize now before it expires!</p>",
            "timestamp": "2026-02-10T09:15:00Z",
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
            "from": {"name": "HR Team", "email": "hr@company.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Benefits enrollment",
            "body": "<p>Open enrollment for benefits begins next week. Please review your options and complete your selections.</p>",
            "timestamp": "2026-02-09T14:00:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
        {
            "id": "email_3",
            "threadId": "thread_3",
            "from": {"name": "SaaS Tool Billing", "email": "billing@saas-tool.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Payment received",
            "body": "<p>We have received your payment. Thank you for your continued subscription.</p>",
            "timestamp": "2026-02-08T10:30:00Z",
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
