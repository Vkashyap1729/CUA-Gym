"""
Golden Patch: Compose and send a new email to jordan@partner.com
Task ID: gmail_030
Domain: mock_websites
Mock: gmail
Changes: Adds one new sent email (folder='sent') to jordan@partner.com with
         subject 'Kickoff scheduling' asking about availability next week.
         Existing emails and empty drafts are left untouched.
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
# Add a new sent email. Do NOT touch email_1/email_2 or drafts.
state['emails'].append({
    'id': 'email_sent_1',
    'threadId': 'thread_sent_1',
    'from': {'name': 'Demo User', 'email': 'demo@example.com'},
    'to': [{'name': 'Jordan', 'email': 'jordan@partner.com'}],
    'cc': [],
    'bcc': [],
    'subject': 'Kickoff scheduling',
    'body': 'Hi Jordan,\n\nI wanted to schedule our project kickoff. Could you '
            'please share your availability for next week? Let me know which '
            'days and times work best for you.\n\nThanks,\nDemo User',
    'timestamp': '2026-07-01T10:00:00Z',
    'read': True,
    'starred': False,
    'important': False,
    'labels': [],
    'category': 'primary',
    'folder': 'sent',
    'attachments': []
})

# --- Write ONLY current_state (preserve initial_state) ---
resp = requests.post(
    f'{BASE_URL}/post?sid={sid}',
    json={'action': 'set_current', 'state': state},
    timeout=30
)
assert resp.status_code == 200, f'set_current failed: {resp.text}'
print(f'Golden state applied via set_current: sid={sid}')

# --- Verify diff exists ---
go2 = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go2['state_diff'], 'state_diff is empty — golden state matches initial (no changes applied)'
print(f'Verified: state_diff is non-empty')
