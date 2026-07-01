"""
Golden Patch: Replace every "ACME" with "Globex" in the "Press Release" document
Task ID: google_docs_017
Domain: mock_websites
Mock: google_docs
Changes: documents[doc-1].content has all three "ACME" occurrences replaced with "Globex".
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
# Replace every "ACME" with "Globex" in the Press Release document content.
doc = state['documents']['doc-1']
doc['content'] = doc['content'].replace('ACME', 'Globex')
assert 'ACME' not in doc['content'], 'ACME still present after replacement'

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
