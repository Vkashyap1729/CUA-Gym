"""
Initial Setup: Report the message pretending to be from my bank as spam.
Task ID: gmail_004
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
# Inbox with 4 emails. email_3 is a phishing email pretending to be from a bank
# (spoofed domain secure-bank-verify.net). Distractors: a genuine invoice (email_1),
# a coworker email (email_2), and a LEGITIMATE bank email from the real domain
# securebank.com (email_4) that must stay in the inbox.
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
            'from': {'name': 'Acme Billing', 'email': 'billing@acme-supplies.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Invoice #4821 for your recent order',
            'body': '<p>Hi,</p><p>Please find your invoice #4821 for $342.00 attached. '
                    'Payment is due within 30 days. Thank you for your business.</p>'
                    '<p>Acme Supplies</p>',
            'timestamp': '2026-06-28T09:12:00Z',
            'read': True,
            'starred': False,
            'important': False,
            'labels': ['l4'],
            'category': 'primary',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            'id': 'email_2',
            'threadId': 'thread_2',
            'from': {'name': 'Jordan Lee', 'email': 'jordan.lee@company.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Slides for Thursday standup',
            'body': '<p>Hey, can you take a look at the slides before Thursday? '
                    'I added the Q3 numbers on slide 4. Thanks!</p><p>Jordan</p>',
            'timestamp': '2026-06-29T14:45:00Z',
            'read': False,
            'starred': False,
            'important': False,
            'labels': ['l1'],
            'category': 'primary',
            'folder': 'inbox',
            'attachments': [],
        },
        {
            'id': 'email_3',
            'threadId': 'thread_3',
            'from': {'name': 'SecureBank Alerts', 'email': 'alerts@secure-bank-verify.net'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Unusual login detected — verify now',
            'body': '<p>Dear Customer,</p><p>We detected an unusual login attempt on your '
                    'account. For your security, you must <a href="http://secure-bank-verify.net/verify">'
                    'verify your identity now</a> or your account will be suspended within 24 hours.</p>'
                    '<p>SecureBank Security Team</p>',
            'timestamp': '2026-06-30T07:03:00Z',
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
            'from': {'name': 'SecureBank', 'email': 'alerts@securebank.com'},
            'to': [{'name': 'Demo User', 'email': 'demo@example.com'}],
            'cc': [],
            'bcc': [],
            'subject': 'Monthly statement ready',
            'body': '<p>Hello,</p><p>Your monthly account statement for June 2026 is now '
                    'available. Log in to your SecureBank dashboard to view it. '
                    'No action is required.</p><p>SecureBank</p>',
            'timestamp': '2026-06-30T06:00:00Z',
            'read': True,
            'starred': False,
            'important': False,
            'labels': ['l4'],
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
