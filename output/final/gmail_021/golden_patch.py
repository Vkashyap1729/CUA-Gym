"""
Golden Patch: Save a draft to alice@company.com titled 'Budget proposal' (don't send)
Task ID: gmail_021
Domain: mock_websites
Mock: gmail_mock
Changes: Add ONE new entry to the drafts array (to alice@company.com, subject
         'Budget proposal', body noting full numbers next week). Nothing added to
         'sent'; inbox email_1 left untouched.
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
# Add a saved draft (NOT a sent email). It lives in the drafts array with folder "drafts".
state['drafts'].append({
    "id": "draft_new_1",
    "threadId": "thread_draft_1",
    "from": {"name": "Demo User", "email": "demo@example.com"},
    "to": [{"name": "", "email": "alice@company.com"}],
    "cc": [],
    "bcc": [],
    "subject": "Budget proposal",
    "body": "Hi Alice, I'll send the full numbers next week.",
    "timestamp": "2026-07-01T10:00:00Z",
    "read": True,
    "starred": False,
    "important": False,
    "labels": [],
    "category": "primary",
    "folder": "drafts",
    "attachments": []
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
cur = go2['current_state']
assert len(cur['drafts']) == 1, 'expected exactly one draft in golden state'
assert not [e for e in cur['emails'] if e.get('folder') == 'sent'], \
    'no email should be in sent folder'
print('Verified: state_diff is non-empty')
