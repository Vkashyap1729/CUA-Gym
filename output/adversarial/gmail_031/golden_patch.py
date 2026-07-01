"""
Golden Patch: Clean up inbox — trash recruiter emails, mark manager email important
Task ID: gmail_031
Domain: mock_websites
Mock: gmail_mock
Changes:
  - email_1, email_2, email_3 (from noreply@jobspam.io): folder inbox -> trash
  - email_4 (from manager@company.com): important false -> true (stays in inbox)
  - email_5 (teammate distractor): unchanged
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
for email in state['emails']:
    if email['id'] in ('email_1', 'email_2', 'email_3'):
        # Move recruiter emails to trash (not permanently deleted)
        email['folder'] = 'trash'
    elif email['id'] == 'email_4':
        # Mark manager email as important (stays in inbox)
        email['important'] = True
    # email_5 (teammate) left untouched

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
