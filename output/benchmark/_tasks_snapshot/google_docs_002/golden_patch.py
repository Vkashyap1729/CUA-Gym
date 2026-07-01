"""
Golden Patch: Rename "Untitled document" to "Sprint Retrospective Notes"
Task ID: google_docs_002
Domain: mock_websites
Mock: google_docs
Changes: documents[doc-1].title -> "Sprint Retrospective Notes" and refresh
         documents[doc-1].updated. doc-2 and doc-3 untouched.
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
# Rename doc-1 and refresh its updated timestamp (mirrors a real rename action).
state['documents']['doc-1']['title'] = 'Sprint Retrospective Notes'
state['documents']['doc-1']['updated'] = '2025-02-18T15:00:00Z'

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
assert go2['current_state']['documents']['doc-1']['title'] == 'Sprint Retrospective Notes'
assert go2['current_state']['documents']['doc-2']['title'] == 'Sprint Planning'
assert go2['current_state']['documents']['doc-3']['title'] == 'Project Proposal'
print('Verified: state_diff is non-empty and doc-1 renamed')
