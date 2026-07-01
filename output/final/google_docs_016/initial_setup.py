"""
Initial Setup: Change the editor to viewing (read-only) mode while reviewing the "Legal Terms" document.
Task ID: google_docs_016
Domain: mock_websites
Mock: google_docs_mock
"""
import json
import os
import shlex
import subprocess
import time
import uuid

import requests

# --- Config ---
BASE_URL = 'https://cua-gym-google-docs.xlang.ai'
sid = str(uuid.uuid4())

# Persist sid for golden_patch.py and reward.py
with open('/tmp/task_web_sid', 'w') as f:
    f.write(sid)

# --- Build initial state ---
# Task NOT yet done: ui.viewMode == "editing" (a fresh reward must score 0.0).
# The "Legal Terms" document (doc-1) is open (ui.currentDocId == "doc-1").
state = {
    'currentUser': {
        'id': 'user-1',
        'name': 'Demo User',
        'email': 'demo@example.com',
        'avatar': 'https://picsum.photos/100/100?random=user1',
    },
    'users': [
        {'id': 'user-1', 'name': 'Demo User', 'email': 'demo@example.com',
         'avatar': 'https://picsum.photos/100/100?random=user1'},
        {'id': 'user-2', 'name': 'Alice Chen', 'email': 'alice@example.com',
         'avatar': 'https://picsum.photos/100/100?random=user2'},
        {'id': 'user-3', 'name': 'Bob Smith', 'email': 'bob@example.com',
         'avatar': 'https://picsum.photos/100/100?random=user3'},
    ],
    'documents': {
        'doc-1': {
            'id': 'doc-1',
            'title': 'Legal Terms',
            'content': (
                '<h1>Legal Terms</h1>'
                '<p>These Terms of Service govern your use of the platform. '
                'By accessing or using the service, you agree to be bound by these terms.</p>'
                '<h2>1. Acceptance of Terms</h2>'
                '<p>You must be at least 18 years of age to use this service.</p>'
                '<h2>2. Limitation of Liability</h2>'
                '<p>The service is provided "as is" without warranties of any kind.</p>'
            ),
            'ownerId': 'user-1',
            'starred': False,
            'created': '2025-01-15T10:00:00Z',
            'updated': '2025-02-18T14:30:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        }
    },
    'comments': [],
    'ui': {
        'currentDocId': 'doc-1',
        'sidebarOpen': False,
        'sidebarTab': 'comments',
        'shareDialogOpen': False,
        'findReplaceOpen': False,
        'viewMode': 'editing',
        'zoom': 100,
        'documentListView': 'grid',
        'searchQuery': '',
    },
}

# --- Inject state ---
resp = requests.post(
    f'{BASE_URL}/post?sid={sid}',
    json={'action': 'set', 'state': state},
    timeout=30,
)
assert resp.status_code == 200, f'State injection failed: {resp.text}'
print(f'State injected: sid={sid}')

# --- Verify ---
go = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go['initial_state'] is not None, 'initial_state is None after injection'
assert go['initial_state']['ui']['viewMode'] == 'editing', 'viewMode should start as editing'
assert go['initial_state']['ui']['currentDocId'] == 'doc-1', 'currentDocId should be doc-1'
print('Verified: initial_state and current_state are set')

# --- Launch browser ---
def launch_gui(command, delay_sec=1.0):
    env = os.environ.copy()
    env['DISPLAY'] = ':0'
    subprocess.Popen(
        shlex.split(command),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    time.sleep(delay_sec)

launch_gui(f'google-chrome "{BASE_URL}/?sid={sid}"', delay_sec=2.0)
print(f'GUI_READY: launched browser at {BASE_URL}/?sid={sid}')
