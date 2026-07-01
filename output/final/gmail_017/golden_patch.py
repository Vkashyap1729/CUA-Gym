"""
Golden Patch: Reply to Bob's invoice email letting him know payment will be sent by Friday.
Task ID: gmail_017
Domain: mock_websites
Mock: gmail_mock
Changes: Adds one new email in the 'sent' folder — a reply to Bob (email_1) on
         threadId 'thread_bob' referencing Invoice #2291, stating payment will
         be sent by Friday. No other email is touched (email_2 gets no reply,
         email_1 preserved).
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
# Add the sent reply to Bob about Invoice #2291. Body states verbatim that
# payment will be sent by Friday.
reply = {
    "id": "email_reply_bob",
    "threadId": "thread_bob",
    "from": {"name": "Demo User", "email": "demo@example.com"},
    "to": [{"name": "Bob Lee", "email": "bob@vendor.io"}],
    "cc": [],
    "bcc": [],
    "subject": "Re: Invoice #2291 due",
    "body": "Hi Bob,<br><br>Thanks for sending Invoice #2291. Payment will be "
            "sent by Friday.<br><br>Best,<br>Demo User",
    "timestamp": "2026-06-30T10:05:00Z",
    "read": True,
    "starred": False,
    "important": False,
    "labels": [],
    "category": "primary",
    "folder": "sent",
    "attachments": [],
}
state["emails"].append(reply)

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
