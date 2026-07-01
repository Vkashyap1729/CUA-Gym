"""
Golden Patch: Append a closing line to the "Runbook" document
Task ID: google_docs_018
Domain: mock_websites
Mock: google_docs
Changes: Append a new paragraph "Prepared by the Operations team." to the
         end of doc-1 ("Runbook") content, preserving all existing content.
"""
import copy
import json

import requests

# --- Config ---
BASE_URL = 'https://cua-gym-google-docs.xlang.ai'

# Read sid from initial_setup.py
with open('/tmp/task_web_sid') as f:
    sid = f.read().strip()

# --- Fetch current initial state ---
go = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
state = copy.deepcopy(go['initial_state'])

# --- Apply ONLY the minimal changes the task requires ---
# Append a new closing paragraph at the END of the Runbook document content,
# preserving the heading and both existing steps in order.
doc = state['documents']['doc-1']
doc['content'] = doc['content'] + '<p>Prepared by the Operations team.</p>'
doc['updated'] = '2025-02-19T09:00:00Z'

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
print('Verified: state_diff is non-empty')
