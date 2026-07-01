"""
Golden Patch: Save a draft email to the finance team reminding them the expense report is due Friday.
Task ID: gmail_032
Domain: mock_websites
Mock: gmail
Changes: Adds ONE draft object to the drafts array (to ana@company.com + paul@company.com,
         subject 'Expense report reminder', body reminding the report is due Friday).
         Does NOT create any email with folder:'sent'. email_1 left untouched.
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
# Save a draft to the whole finance team. It must remain a draft (never sent).
state['drafts'].append({
    "id": "draft_1",
    "threadId": "draft_thread_1",
    "from": {"name": "Demo User", "email": "demo@example.com"},
    "to": [
        {"name": "Ana", "email": "ana@company.com"},
        {"name": "Paul", "email": "paul@company.com"},
    ],
    "cc": [],
    "bcc": [],
    "subject": "Expense report reminder",
    "body": "Hi team, this is a friendly reminder that the expense report is due Friday. "
            "Please make sure to submit it on time.",
    "timestamp": "2026-06-30T10:00:00Z",
    "read": True,
    "starred": False,
    "important": False,
    "labels": [],
    "category": "primary",
    "folder": "drafts",
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
print(f'Verified: state_diff is non-empty')
