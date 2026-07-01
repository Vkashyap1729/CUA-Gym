"""
Golden Patch: Compose and send a new email to hr@company.com requesting Friday off for a doctor's appointment.
Task ID: gmail_019
Domain: mock_websites
Mock: gmail

Changes (touch nothing else):
  - Append ONE new email to `emails` in folder 'sent', from Demo User to hr@company.com,
    whose subject clearly signals a time-off / leave request and whose body explicitly
    requests Friday off for a doctor's appointment.
  - Distractors (email_1, email_2) and drafts remain exactly as in the initial state.
"""
import copy

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
# Add a new sent email requesting Friday off for a doctor's appointment.
# Inbox emails (email_1, email_2) and drafts remain untouched.
state['emails'].append({
    "id": "email_sent_1",
    "threadId": "thread_sent_1",
    "from": {"name": "Demo User", "email": "demo@example.com"},
    "to": [{"name": "HR", "email": "hr@company.com"}],
    "cc": [],
    "bcc": [],
    "subject": "Leave Request: Friday Off for Doctor's Appointment",
    "body": (
        "Hi HR,<br><br>"
        "I would like to request this Friday off as I have a doctor's appointment "
        "scheduled that day. I will not be available to work on Friday.<br><br>"
        "Please let me know if you need any additional information or paperwork to "
        "approve the time off.<br><br>"
        "Thank you,<br>Demo User"
    ),
    "snippet": "I would like to request this Friday off for a doctor's appointment.",
    "timestamp": "2026-07-01T10:00:00Z",
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
