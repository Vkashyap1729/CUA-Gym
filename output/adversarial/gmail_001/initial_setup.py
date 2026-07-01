"""
Initial Setup: Star the email from Alice Chen about the quarterly budget
Task ID: gmail_001
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
# Inbox with 4 emails, ALL starred=false (task not yet done → reward = 0.0).
# email_1 is the target (Alice Chen, quarterly budget). The other three are
# distractors that must stay untouched — note email_3 is ALSO from Alice Chen
# (same sender, different subject) and must NOT be starred.
state = {
    'user': {
        'userId': 'u1',
        'username': 'Demo User',
        'email': 'demo@example.com',
        'avatar': '',
    },
    'emails': [
        {
            'id': 'email_1',
            'threadId': 'thread_1',
            'from': {'name': 'Alice Chen', 'email': 'alice.chen@finance.co', 'avatar': ''},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Q3 Quarterly Budget Review',
            'body': '<p>Hi team, please review the Q3 quarterly budget ahead of our meeting.</p>',
            'timestamp': '2026-06-20T09:15:00Z',
            'read': False,
            'starred': False,
            'important': False,
            'labels': [],
            'category': 'primary',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            'id': 'email_2',
            'threadId': 'thread_2',
            'from': {'name': 'Bob Ng', 'email': 'bob.ng@company.com', 'avatar': ''},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Team lunch Friday',
            'body': '<p>Anyone up for team lunch this Friday?</p>',
            'timestamp': '2026-06-19T12:00:00Z',
            'read': False,
            'starred': False,
            'important': False,
            'labels': [],
            'category': 'primary',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            'id': 'email_3',
            'threadId': 'thread_3',
            'from': {'name': 'Alice Chen', 'email': 'alice.chen@finance.co', 'avatar': ''},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Out of office next week',
            'body': '<p>I will be out of office next week. Please reach out to Bob for urgent items.</p>',
            'timestamp': '2026-06-18T16:45:00Z',
            'read': False,
            'starred': False,
            'important': False,
            'labels': [],
            'category': 'primary',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            'id': 'email_4',
            'threadId': 'thread_4',
            'from': {'name': 'Retail Newsletter', 'email': 'newsletter@retail.com', 'avatar': ''},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Summer Sale',
            'body': '<p>Big summer sale — up to 50% off!</p>',
            'timestamp': '2026-06-17T08:00:00Z',
            'read': False,
            'starred': False,
            'important': False,
            'labels': [],
            'category': 'promotions',
            'folder': 'inbox',
            'attachments': [],
        },
    ],
    'labels': [
        {'id': 'l1', 'name': 'Work', 'color': '#ef4444'},
        {'id': 'l2', 'name': 'Personal', 'color': '#3b82f6'},
        {'id': 'l3', 'name': 'Travel', 'color': '#22c55e'},
        {'id': 'l4', 'name': 'Finance', 'color': '#eab308'},
    ],
    'drafts': [],
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
assert len(go['initial_state']['emails']) == 4, 'expected 4 emails in initial state'
assert all(not e['starred'] for e in go['initial_state']['emails']), 'no email should be starred initially'
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
