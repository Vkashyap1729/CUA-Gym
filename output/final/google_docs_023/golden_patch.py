"""
Golden Patch: Star both "Q1 OKRs" and "Q2 OKRs" so the quarterly goal docs stay at the top.
Task ID: google_docs_023
Domain: mock_websites
Mock: google_docs
Changes: set documents['doc-1'].starred = True and documents['doc-2'].starred = True.
         doc-3 (Q3 OKRs) is left unstarred.
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
# Star Q1 OKRs (doc-1) and Q2 OKRs (doc-2). Leave Q3 OKRs (doc-3) untouched.
state['documents']['doc-1']['starred'] = True
state['documents']['doc-2']['starred'] = True

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
assert go2['current_state']['documents']['doc-1']['starred'] is True, 'doc-1 should be starred'
assert go2['current_state']['documents']['doc-2']['starred'] is True, 'doc-2 should be starred'
assert go2['current_state']['documents']['doc-3']['starred'] is False, 'doc-3 must remain unstarred'
print(f'Verified: state_diff is non-empty')
