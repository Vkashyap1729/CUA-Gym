"""
Initial Setup: Open and read the message from IT Support about the password reset.
Task ID: gmail_002
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
# Inbox with 5 emails, all unread. email_2 is the IT Support password-reset
# message the task targets. email_3 is a distractor from the SAME sender
# (IT Support) but a different subject — it must stay unread.
state = {
    'user': {
        'userId': 'u1',
        'username': 'Demo User',
        'email': 'demo@example.com',
    },
    'emails': [
        {
            'id': 'email_1',
            'threadId': 'thread_1',
            'from': {'name': 'HR Department', 'email': 'hr@corp.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Updated employee handbook for 2026',
            'body': '<p>Hello team, the updated employee handbook is now '
                    'available on the intranet. Please review it at your '
                    'convenience.</p>',
            'timestamp': '2026-06-28T15:20:00Z',
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
            'from': {'name': 'IT Support', 'email': 'it-support@corp.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Action required: reset your password',
            'body': '<p>Dear user,</p><p>Our records indicate that your '
                    'corporate account password is due to expire. Please reset '
                    'your password within 48 hours to avoid losing access. '
                    'Follow the instructions on the company portal to complete '
                    'the reset.</p><p>Thank you,<br>IT Support</p>',
            'timestamp': '2026-06-28T14:02:00Z',
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
            'from': {'name': 'IT Support', 'email': 'it-support@corp.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Scheduled maintenance Saturday',
            'body': '<p>Please be advised that scheduled maintenance will take '
                    'place this Saturday from 02:00 to 06:00. Some services may '
                    'be temporarily unavailable during this window.</p>',
            'timestamp': '2026-06-27T09:45:00Z',
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
            'from': {'name': 'Jordan Lee', 'email': 'jordan.lee@company.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Lunch next week?',
            'body': '<p>Hey! Are you free for lunch sometime next week? Let me '
                    'know what day works for you.</p>',
            'timestamp': '2026-06-26T12:10:00Z',
            'read': False,
            'starred': False,
            'important': False,
            'labels': [],
            'category': 'primary',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            'id': 'email_5',
            'threadId': 'thread_5',
            'from': {'name': 'Newsletter', 'email': 'news@techweekly.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'This week in tech',
            'body': '<p>Your weekly roundup of the biggest stories in tech is '
                    'here. Read on for the highlights.</p>',
            'timestamp': '2026-06-25T08:00:00Z',
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
    timeout=30,
)
assert resp.status_code == 200, f'State injection failed: {resp.text}'
print(f'State injected: sid={sid}')

# --- Verify ---
go = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go['initial_state'] is not None, 'initial_state is None after injection'
assert len(go['initial_state']['emails']) == 5, 'expected 5 emails in inbox'
assert all(not e['read'] for e in go['initial_state']['emails']), \
    'all emails must start unread (task not yet done)'
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
