"""
Golden Patch: File company.com colleague emails under Work label + mark read
Task ID: gmail_023
Domain: mock_websites
Mock: gmail
Changes: email_1/2/3 (company.com senders) get label 'l1' AND read:true.
         email_4 (vendor@outside.io) and email_5 (noreply@company-news.com)
         are left completely untouched.
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
# company.com colleagues -> add 'l1' (Work) label + mark read.
COMPANY_INTERNAL = {'email_1', 'email_2', 'email_3'}
for email in state['emails']:
    if email['id'] in COMPANY_INTERNAL:
        email['read'] = True
        if 'l1' not in email['labels']:
            email['labels'] = email['labels'] + ['l1']
    # email_4 and email_5 are intentionally left untouched.

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
