"""
Golden Patch: Unstar the "Vacation Itinerary" document
Task ID: google_docs_006
Domain: mock_websites
Mock: google_docs
Changes: documents[doc-1].starred -> False (doc-2 and doc-3 untouched)
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
# Unstar the "Vacation Itinerary" document (doc-1). Touch nothing else.
state['documents']['doc-1']['starred'] = False

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
assert go2['current_state']['documents']['doc-1']['starred'] is False, 'doc-1 should be unstarred'
assert go2['current_state']['documents']['doc-2']['starred'] is True, 'doc-2 must stay starred'
assert go2['current_state']['documents']['doc-3']['starred'] is False, 'doc-3 must stay unstarred'
print('Verified: state_diff is non-empty')
