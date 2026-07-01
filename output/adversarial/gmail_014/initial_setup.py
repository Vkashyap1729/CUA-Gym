"""
Initial Setup: Open and read the unread message from the recruiter.
Task ID: gmail_014
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
# Inbox has 3 emails:
#  (1) email_1 from Dana Recruiter, unread  -> the target message
#  (2) email_2 from Dana Recruiter, already read (distractor: same sender, must stay read:true)
#  (3) email_3 from team@updates.com, unread (distractor: different sender, must stay read:false)
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
            'from': {'name': 'Dana Recruiter', 'email': 'dana@talenthub.co'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Interview scheduling for Senior Engineer role',
            'body': '<p>Hi, I would love to schedule an interview for the Senior '
                    'Engineer role. Are you available next week?</p>',
            'timestamp': '2026-06-30T09:15:00Z',
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
            'from': {'name': 'Dana Recruiter', 'email': 'dana@talenthub.co'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Re: your application',
            'body': '<p>Thanks for applying! We received your application and will '
                    'be in touch soon.</p>',
            'timestamp': '2026-06-28T14:00:00Z',
            'read': True,
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
            'from': {'name': 'Team Updates', 'email': 'team@updates.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Sprint summary',
            'body': '<p>Here is the sprint summary for this week.</p>',
            'timestamp': '2026-06-29T17:30:00Z',
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
