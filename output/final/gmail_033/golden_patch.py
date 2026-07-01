"""
Golden Patch: Permanently delete the phishing email in Spam from security-alert@paypa1.com
Task ID: gmail_033
Domain: mock_websites
Mock: gmail_mock
Changes: Remove email_1 (phishing, folder='spam') from the emails array entirely.
         email_2 (spam distractor) and email_3 (inbox distractor) are left untouched.
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
# Permanently delete email_1: remove it entirely from the emails array.
before = [e['id'] for e in state['emails']]
state['emails'] = [e for e in state['emails'] if e['id'] != 'email_1']
after = [e['id'] for e in state['emails']]
assert after == ['email_2', 'email_3'], f'Unexpected result after deletion: {after}'
print(f'emails: {before} -> {after}')

# --- Write ONLY current_state (preserve initial_state) ---
resp = requests.post(
    f'{BASE_URL}/post?sid={sid}',
    json={'action': 'set_current', 'state': state},
    timeout=30
)
assert resp.status_code == 200, f'set_current failed: {resp.text}'
print(f'Golden state applied via set_current: sid={sid}')

# --- Verify diff exists ---
# The mock computes a generic per-key diff: emails change surfaces as
# state_diff['emails'] (not a dedicated 'deletedEmails' list). Confirm the
# emails key changed and that email_1 is gone from current_state.
go2 = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go2['state_diff'], 'state_diff is empty — golden state matches initial (no changes applied)'
assert 'emails' in go2['state_diff'], \
    f"emails key not in state_diff: {go2['state_diff']}"
current_ids = [e['id'] for e in go2['current_state']['emails']]
assert current_ids == ['email_2', 'email_3'], \
    f'Unexpected current emails after deletion: {current_ids}'
initial_ids = [e['id'] for e in go2['initial_state']['emails']]
assert initial_ids == ['email_1', 'email_2', 'email_3'], \
    f'initial_state was corrupted (should be untouched): {initial_ids}'
print(f'Verified: email_1 permanently deleted. current emails = {current_ids}')
