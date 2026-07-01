"""
Initial Setup: Clean up inbox — trash recruiter emails, mark manager email important
Task ID: gmail_031
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
# Task NOT yet done: all recruiter emails are in inbox (not trash),
# manager email is important:false, distractor teammate email untouched.
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
            'from': {'name': 'JobSpam Recruiting', 'email': 'noreply@jobspam.io'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Exciting opportunity',
            'body': '<p>We have an exciting opportunity for you! Apply now.</p>',
            'timestamp': '2026-06-25T09:00:00Z',
            'read': False,
            'starred': False,
            'important': False,
            'labels': [],
            'category': 'promotions',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            'id': 'email_2',
            'threadId': 'thread_2',
            'from': {'name': 'JobSpam Recruiting', 'email': 'noreply@jobspam.io'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Follow up',
            'body': '<p>Just following up on our last email. Are you interested?</p>',
            'timestamp': '2026-06-26T10:15:00Z',
            'read': False,
            'starred': False,
            'important': False,
            'labels': [],
            'category': 'promotions',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            'id': 'email_3',
            'threadId': 'thread_3',
            'from': {'name': 'JobSpam Recruiting', 'email': 'noreply@jobspam.io'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Last chance',
            'body': '<p>This is your last chance to apply for this role!</p>',
            'timestamp': '2026-06-27T08:30:00Z',
            'read': False,
            'starred': False,
            'important': False,
            'labels': [],
            'category': 'promotions',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            'id': 'email_4',
            'threadId': 'thread_4',
            'from': {'name': 'Manager', 'email': 'manager@company.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Your Q4 objectives',
            'body': '<p>Please review your Q4 objectives before our next 1:1.</p>',
            'timestamp': '2026-06-28T14:00:00Z',
            'read': True,
            'starred': False,
            'important': False,
            'labels': ['l1'],
            'category': 'primary',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            'id': 'email_5',
            'threadId': 'thread_5',
            'from': {'name': 'Teammate', 'email': 'teammate@company.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Lunch?',
            'body': '<p>Want to grab lunch tomorrow?</p>',
            'timestamp': '2026-06-29T11:45:00Z',
            'read': False,
            'starred': False,
            'important': False,
            'labels': [],
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
