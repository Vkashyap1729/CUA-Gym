"""
Golden Patch: Reply to Carol's email confirming attendance at Thursday design review
Task ID: gmail_029
Domain: mock_websites
Mock: gmail
Changes: mark Carol's email read; add a new 'sent' email in thread_5 to Carol
         confirming attendance. email_2 (Dave) untouched.
"""
import copy
import json

import requests

# --- Config ---
BASE_URL = 'https://cua-gym-gmail.xlang.ai'

# Read sid from initial_setup.py
with open('/tmp/task_web_sid') as f:
    sid = f.read().strip()

# --- Fetch current initial state ---
go = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
state = copy.deepcopy(go['initial_state'])

# --- Apply ONLY the minimal changes the task requires ---
# Reading Carol's email is acceptable as part of replying.
for email in state['emails']:
    if email['id'] == 'email_1':
        email['read'] = True

# Add the reply: a new email in the 'sent' folder, same thread as Carol's message,
# addressed to Carol, affirmatively confirming attendance.
state['emails'].append({
    'id': 'email_sent_1',
    'threadId': 'thread_5',
    'from': {'name': 'Demo User', 'email': 'demo@example.com'},
    'to': [{'name': 'Carol Nguyen', 'email': 'carol@company.com'}],
    'cc': [],
    'bcc': [],
    'subject': 'Re: Design review Thursday 2pm',
    'body': (
        '<p>Hi Carol,</p>'
        '<p>Yes, I will attend the design review on Thursday at 2pm. '
        'See you then!</p>'
        '<p>Best,<br>Demo</p>'
    ),
    'timestamp': '2026-06-29T10:05:00Z',
    'read': True,
    'starred': False,
    'important': False,
    'labels': [],
    'category': 'primary',
    'folder': 'sent',
    'attachments': [],
})

# --- Write ONLY current_state (preserve initial_state) ---
resp = requests.post(
    f'{BASE_URL}/post?sid={sid}',
    json={'action': 'set_current', 'state': state},
    timeout=30,
)
assert resp.status_code == 200, f'set_current failed: {resp.text}'
print(f'Golden state applied via set_current: sid={sid}')

# --- Verify diff exists ---
go2 = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go2['state_diff'], 'state_diff is empty — golden state matches initial (no changes applied)'
print('Verified: state_diff is non-empty')
