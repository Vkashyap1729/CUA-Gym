"""
Initial Setup: Move the promotional ShopMart email to trash
Task ID: gmail_003
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
# Inbox with 4 emails. email_4 is the junk ShopMart promo to be trashed.
# Distractors (email_1, email_2, email_3) must stay in inbox.
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
            "from": {"name": "Priya Nair", "email": "priya.nair@company.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Re: Sprint planning notes",
            "body": "<p>Thanks for the notes — I've added a few comments inline. Let's sync tomorrow.</p>",
            "timestamp": "2026-06-29T09:15:00Z",
            "read": True,
            "starred": False,
            "important": True,
            "labels": ["l1"],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
        {
            "id": "email_2",
            "threadId": "thread_2",
            "from": {"name": "First National Bank", "email": "no-reply@firstnational.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Your June statement is ready",
            "body": "<p>Your monthly account statement is now available. Log in to view it securely.</p>",
            "timestamp": "2026-06-28T07:00:00Z",
            "read": False,
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
            "from": {"name": "RetailPlus", "email": "orders@retailplus.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Your order shipped",
            "body": "<p>Good news! Your order #RP-48213 has shipped and is on its way. Track your package for delivery updates.</p>",
            "timestamp": "2026-06-27T16:42:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": [],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
        {
            "id": "email_4",
            "threadId": "thread_4",
            "from": {"name": "ShopMart Deals", "email": "deals@shopmart.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "70% off everything this weekend",
            "body": "<p>HUGE weekend blowout! Get 70% off everything storewide. Shop now before it's gone!</p>",
            "timestamp": "2026-06-30T05:30:00Z",
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
emails = {e['id']: e for e in go['initial_state']['emails']}
assert emails['email_4']['folder'] == 'inbox', 'email_4 should start in inbox (task not yet done)'
print('Verified: initial_state and current_state are set; ShopMart email in inbox')

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
