"""
Golden Patch: Draft an email to a vendor requesting an updated price quote (do not send)
Task ID: gmail_007
Domain: mock_websites
Mock: gmail
Changes: Add ONE new draft to the drafts array addressed to procurement@acmesupplies.com
         requesting an updated price quote for 200 office chairs. Nothing sent; inbox
         distractors untouched.
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
# The task is to draft (NOT send) an email. So we add a single new draft object to
# the drafts array. We touch nothing else: inbox distractors and sent folder stay
# exactly as they were.
new_draft = {
    'id': 'draft_new_1',
    'threadId': 'thread_draft_new_1',
    'from': {'name': 'Demo User', 'email': 'demo@example.com', 'avatar': ''},
    'to': [{'name': '', 'email': 'procurement@acmesupplies.com'}],
    'cc': [],
    'bcc': [],
    'subject': 'Request for Updated Price Quote — 200 Office Chairs',
    'body': (
        'Hello,\n\n'
        'We would like to request an updated price quote for 200 office chairs. '
        'Could you please provide your current pricing, including any available '
        'bulk discounts, along with estimated lead time and shipping costs?\n\n'
        'Thank you,\n'
        'Demo User'
    ),
    'timestamp': '2026-07-01T10:00:00Z',
    'read': True,
    'starred': False,
    'important': False,
    'labels': [],
    'category': 'primary',
    'folder': 'drafts',
    'attachments': [],
}
state['drafts'].append(new_draft)

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
assert len(go2['current_state']['drafts']) == 1, 'expected exactly one draft in golden state'
# Ensure nothing was sent
sent = [e for e in go2['current_state']['emails'] if e.get('folder') == 'sent']
assert sent == [], 'no email should be in the sent folder (must not be sent)'
print('Verified: state_diff is non-empty')
