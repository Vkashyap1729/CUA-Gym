"""
Golden Patch: Forward Marcus's project brief to dana@corp.com (cc Marcus) and label original as Work
Task ID: gmail_011
Domain: mock_websites
Mock: gmail_mock
Changes (touch nothing else):
  1. email_1.labels -> ['l1'] (Work).
  2. Append a NEW email in folder 'sent' from demo@example.com,
     to dana@corp.com, cc marcus@corp.com, subject 'Fwd: Project Atlas brief',
     body carrying the original brief content.
  email_2/email_3/email_4 untouched; drafts stays empty (no draft left behind).
"""
import copy

import requests

# --- Config ---
BASE_URL = 'https://cua-gym-gmail.xlang.ai'

# Read sid from initial_setup.py
with open('/tmp/task_web_sid') as f:
    sid = f.read().strip()

# --- Fetch initial state and deep-copy it ---
go = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
state = copy.deepcopy(go['initial_state'])

# --- Locate the original brief email (email_1) ---
brief = next(e for e in state['emails'] if e['id'] == 'email_1')

# 1) Label the original as Work (l1). Leave everything else on email_1 as-is.
brief['labels'] = ['l1']

# 2) Append the forwarded email in the 'sent' folder, carrying the brief body.
forwarded_body = (
    "<p>---------- Forwarded message ----------<br/>"
    "From: Marcus Lee &lt;marcus@corp.com&gt;<br/>"
    "Subject: Project Atlas brief</p>"
    + brief['body']
)

state['emails'].append({
    "id": "email_fwd_1",
    "threadId": "thread_fwd_9",
    "from": {"name": "Demo User", "email": "demo@example.com", "avatar": ""},
    "to": [{"name": "Dana", "email": "dana@corp.com"}],
    "cc": [{"name": "Marcus Lee", "email": "marcus@corp.com"}],
    "bcc": [],
    "subject": "Fwd: Project Atlas brief",
    "body": forwarded_body,
    "timestamp": "2026-06-28T10:00:00Z",
    "read": True,
    "starred": False,
    "important": False,
    "labels": [],
    "category": "primary",
    "folder": "sent",
    "attachments": [],
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
print('DONE')
