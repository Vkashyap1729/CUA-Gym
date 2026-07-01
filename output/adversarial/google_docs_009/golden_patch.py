"""
Golden Patch: Turn on link sharing for "Customer FAQ" so anyone with the link can view it.
Task ID: google_docs_009
Domain: mock_websites
Mock: google_docs
Changes: documents[doc-1].linkSharing.enabled -> True (permission stays "viewer"). doc-2 untouched.
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
# Enable link sharing on "Customer FAQ" (doc-1); permission remains "viewer".
state['documents']['doc-1']['linkSharing']['enabled'] = True
state['documents']['doc-1']['linkSharing']['permission'] = 'viewer'
# doc-2 ("Internal Wiki") link sharing must remain disabled — touch nothing else.

# --- Write ONLY current_state (preserve initial_state) ---
resp = requests.post(
    f'{BASE_URL}/post?sid={sid}',
    json={'action': 'set_current', 'state': state},
    timeout=30
)
assert resp.status_code == 200, f'set_current failed: {resp.text}'
print(f'Golden state applied via set_current: sid={sid}')

# --- Verify diff exists and is scoped to doc-1 only ---
go2 = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go2['state_diff'], 'state_diff is empty — golden state matches initial (no changes applied)'
assert go2['current_state']['documents']['doc-1']['linkSharing']['enabled'] is True
assert go2['current_state']['documents']['doc-1']['linkSharing']['permission'] == 'viewer'
assert go2['current_state']['documents']['doc-2']['linkSharing']['enabled'] is False
print('Verified: state_diff is non-empty')
