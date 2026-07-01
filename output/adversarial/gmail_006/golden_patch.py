"""
Golden Patch: Reply to Priya's email about the design review (3pm Thursday slot)
Task ID: gmail_006
Domain: mock_websites
Mock: gmail
Changes: Add ONE new email to the 'sent' folder — a reply in thread_1 from the
         demo user to Priya, subject 'Re: Design review scheduling', body
         confirming availability for the 3pm Thursday slot. Nothing else changes.
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
# Send a reply to Priya in thread_1 → new email in the 'sent' folder.
# Original email_1 and both distractors remain untouched; no draft created.
sent_reply = {
    "id": "email_sent_1",
    "threadId": "thread_1",
    "from": {"name": "Demo User", "email": "demo@example.com"},
    "to": [{"name": "Priya Raman", "email": "priya@studio.design"}],
    "cc": [],
    "bcc": [],
    "subject": "Re: Design review scheduling",
    "body": "Hi Priya,<br><br>Thanks for reaching out. Yes, I am available "
            "and can make the 3pm slot on Thursday for the design review. "
            "That time works for me and I will be there.<br><br>"
            "Best,<br>Demo User",
    "timestamp": "2026-06-29T11:15:00Z",
    "read": True,
    "starred": False,
    "important": False,
    "labels": [],
    "category": "primary",
    "folder": "sent",
    "attachments": [],
}
state["emails"].append(sent_reply)

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
