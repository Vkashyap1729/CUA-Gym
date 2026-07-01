"""
Initial Setup: Move the 'Weekly Deals' promotional email to spam.
Task ID: gmail_027
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
# Inbox has three emails, all in folder:inbox (task NOT yet done).
#   email_1 = the 'Weekly Deals' promo (the target to move to spam)
#   email_2 = distractor: same sender, legitimate order shipment — stays in inbox
#   email_3 = distractor: subject contains 'Deals' but real work email — stays in inbox
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
            'from': {'name': 'ShopMart', 'email': 'newsletter@shopmart.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Weekly Deals - 50% off',
            'body': '<p>Our biggest sale of the week! Get 50% off storewide. Shop now before these deals expire.</p>',
            'timestamp': '2026-02-09T09:15:00Z',
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
            'from': {'name': 'ShopMart', 'email': 'newsletter@shopmart.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Your order shipped',
            'body': '<p>Good news! Your recent order has shipped and is on its way. Track your package for delivery updates.</p>',
            'timestamp': '2026-02-09T10:40:00Z',
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
            'from': {'name': 'Manager', 'email': 'manager@company.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Deals proposal draft',
            'body': '<p>Hi, please take a look at the attached deals proposal draft and share your feedback before Friday.</p>',
            'timestamp': '2026-02-09T11:20:00Z',
            'read': False,
            'starred': False,
            'important': True,
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
