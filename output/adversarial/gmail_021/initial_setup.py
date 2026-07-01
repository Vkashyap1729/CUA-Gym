"""
Initial Setup: Save a draft to alice@company.com titled 'Budget proposal' (don't send)
Task ID: gmail_021
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
# Task NOT yet done: drafts empty, no email in 'sent'. Inbox has one context email
# from alice@company.com. Provide ALL required top-level keys from the schema.
state = {
    "user": {"userId": "u1", "username": "Demo User", "email": "demo@example.com"},
    "emails": [
        {
            "id": "email_1",
            "threadId": "thread_1",
            "from": {"name": "Alice", "email": "alice@company.com"},
            "to": [{"name": "Demo User", "email": "demo@example.com"}],
            "cc": [],
            "bcc": [],
            "subject": "Re: Budget",
            "body": "Hi, following up on the budget discussion. Let me know when you have the proposal ready.",
            "timestamp": "2026-06-28T09:15:00Z",
            "read": False,
            "starred": False,
            "important": False,
            "labels": ["l4"],
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
assert go['initial_state']['drafts'] == [], 'drafts should be empty in initial state'
assert not [e for e in go['initial_state']['emails'] if e.get('folder') == 'sent'], \
    'sent folder should be empty in initial state'
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
