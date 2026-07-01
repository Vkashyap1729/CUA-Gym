"""
Initial Setup: Clean up inbox — mark two unread newsletters as read and archive them.
Task ID: gmail_008
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
# 5 emails in the inbox. The task is NOT yet done: the two newsletters
# (email_2, email_4) are unread and still in the inbox.
state = {
    'user': {
        'userId': 'u1',
        'username': 'Demo User',
        'email': 'demo@example.com',
        'avatar': '',
    },
    'emails': [
        {
            # Distractor: real work email from a manager — must stay inbox + unread.
            'id': 'email_1',
            'threadId': 'thread_1',
            'from': {'name': 'Sarah Chen', 'email': 'sarah.chen@company.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Q3 planning review — need your input by Friday',
            'body': '<p>Hi, can you send over your team\'s Q3 priorities before our '
                    'sync on Friday? Want to make sure we align budgets.</p>',
            'timestamp': '2026-06-29T09:15:00Z',
            'read': False,
            'starred': False,
            'important': True,
            'labels': ['l1'],
            'category': 'primary',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            # Newsletter #1 — target: mark read + archive.
            'id': 'email_2',
            'threadId': 'thread_2',
            'from': {'name': 'Weekly Tech Digest', 'email': 'news@techdigest.io'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'This week in tech: 5 stories you should know',
            'body': '<p>Your weekly roundup of the biggest stories in tech. '
                    'Read on for our top picks.</p>',
            'timestamp': '2026-06-28T07:00:00Z',
            'read': False,
            'starred': False,
            'important': False,
            'labels': [],
            'category': 'promotions',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            # Distractor: already read, stays inbox.
            'id': 'email_3',
            'threadId': 'thread_3',
            'from': {'name': 'Building Management', 'email': 'noreply@buildingmgmt.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Elevator maintenance scheduled for Monday',
            'body': '<p>Please note the north elevator will be out of service '
                    'Monday from 8am-12pm.</p>',
            'timestamp': '2026-06-27T14:30:00Z',
            'read': True,
            'starred': False,
            'important': False,
            'labels': [],
            'category': 'primary',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            # Newsletter #2 — target: mark read + archive.
            'id': 'email_4',
            'threadId': 'thread_4',
            'from': {'name': 'Marketing Weekly', 'email': 'hello@mktgweekly.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Marketing Weekly: trends, tips & tools',
            'body': '<p>The latest marketing trends and growth tactics, '
                    'delivered every week.</p>',
            'timestamp': '2026-06-26T06:45:00Z',
            'read': False,
            'starred': False,
            'important': False,
            'labels': [],
            'category': 'promotions',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            # Distractor: from a friend, unread — stays inbox + unread.
            'id': 'email_5',
            'threadId': 'thread_5',
            'from': {'name': 'Jamie Rivera', 'email': 'jamie.rivera@gmail.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Dinner this weekend?',
            'body': '<p>Hey! Are you free Saturday night? Thinking about trying '
                    'that new ramen place downtown.</p>',
            'timestamp': '2026-06-25T20:10:00Z',
            'read': False,
            'starred': False,
            'important': False,
            'labels': ['l2'],
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
