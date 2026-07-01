"""
Initial Setup: Draft an email to a vendor requesting an updated price quote (do not send)
Task ID: gmail_007
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
# Task NOT yet done: drafts is empty, no email to procurement@acmesupplies.com
# exists anywhere. Inbox holds 3 unrelated distractor emails that must stay untouched.
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
            'from': {'name': 'Alice Smith', 'email': 'alice@company.com', 'avatar': ''},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Q4 Project Roadmap Update',
            'body': 'Hi, please review the attached roadmap when you get a chance.',
            'timestamp': '2026-06-25T11:30:00Z',
            'read': False,
            'starred': True,
            'important': True,
            'labels': ['l1'],
            'category': 'primary',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            'id': 'email_2',
            'threadId': 'thread_2',
            'from': {'name': 'Weekend Getaways', 'email': 'deals@weekendgetaways.com', 'avatar': ''},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Your summer travel deals are here',
            'body': 'Book now and save 30% on your next weekend escape.',
            'timestamp': '2026-06-26T08:05:00Z',
            'read': True,
            'starred': False,
            'important': False,
            'labels': ['l3'],
            'category': 'promotions',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            'id': 'email_3',
            'threadId': 'thread_3',
            'from': {'name': 'HR Team', 'email': 'hr@company.com', 'avatar': ''},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Reminder: Submit your timesheet by Friday',
            'body': 'This is a friendly reminder to submit your timesheet before end of week.',
            'timestamp': '2026-06-29T09:00:00Z',
            'read': False,
            'starred': False,
            'important': False,
            'labels': ['l1'],
            'category': 'primary',
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
    timeout=30,
)
assert resp.status_code == 200, f'State injection failed: {resp.text}'
print(f'State injected: sid={sid}')

# --- Verify ---
go = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go['initial_state'] is not None, 'initial_state is None after injection'
assert go['initial_state']['drafts'] == [], 'drafts should start empty'
assert len(go['initial_state']['emails']) == 3, 'expected 3 inbox distractor emails'
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
