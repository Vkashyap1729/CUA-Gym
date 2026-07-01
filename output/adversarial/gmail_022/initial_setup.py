"""
Initial Setup: Clean up starred items — unstar promo emails, keep work email starred + important
Task ID: gmail_022
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
# 3 starred emails (all starred:true, important:false) + 1 non-starred distractor.
# Task is NOT yet done: promos still starred, work email not yet important.
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
            "from": {"name": "Shop Deals", "email": "deals@shop.com", "avatar": ""},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Flash sale",
            "body": "<p>Huge flash sale — up to 70% off everything today only!</p>",
            "snippet": "Huge flash sale — up to 70% off everything today only!",
            "timestamp": "2026-06-28T09:15:00Z",
            "read": True,
            "starred": True,
            "important": False,
            "labels": [],
            "category": "promotions",
            "folder": "inbox",
            "attachments": [],
        },
        {
            "id": "email_2",
            "threadId": "thread_2",
            "from": {"name": "Retail Offers", "email": "offers@retail.com", "avatar": ""},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Coupon inside",
            "body": "<p>Your exclusive coupon is waiting. Use code SAVE20 at checkout.</p>",
            "snippet": "Your exclusive coupon is waiting. Use code SAVE20 at checkout.",
            "timestamp": "2026-06-28T10:40:00Z",
            "read": True,
            "starred": True,
            "important": False,
            "labels": [],
            "category": "promotions",
            "folder": "inbox",
            "attachments": [],
        },
        {
            "id": "email_3",
            "threadId": "thread_3",
            "from": {"name": "Manager", "email": "manager@company.com", "avatar": ""},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Perf review draft",
            "body": "<p>Here is the draft of your performance review. Please take a look before our 1:1.</p>",
            "snippet": "Here is the draft of your performance review. Please take a look before our 1:1.",
            "timestamp": "2026-06-28T14:05:00Z",
            "read": True,
            "starred": True,
            "important": False,
            "labels": [],
            "category": "primary",
            "folder": "inbox",
            "attachments": [],
        },
        {
            "id": "email_4",
            "threadId": "thread_4",
            "from": {"name": "Unknown Sender", "email": "spam@x.com", "avatar": ""},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "You have won a prize",
            "body": "<p>Click here to claim your prize now!</p>",
            "snippet": "Click here to claim your prize now!",
            "timestamp": "2026-06-28T08:00:00Z",
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
