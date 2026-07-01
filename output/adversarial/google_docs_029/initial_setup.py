"""
Initial Setup: Add a comment on the "Recipe Collection" document quoting the "Recipes" heading
Task ID: google_docs_029
Domain: mock_websites
Mock: google_docs
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
# Per google_docs_mock schema: required top-level keys are
# currentUser, users, documents, comments, ui.
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
            'title': 'Recipe Collection',
            'content': '<h1>Recipes</h1><p>Pasta, salad, and soup.</p>',
            'ownerId': 'user-1',
            'starred': False,
            'created': '2025-01-15T10:00:00Z',
            'updated': '2025-02-18T14:30:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
    },
    # Task is NOT yet done: no comments exist.
    'comments': [],
    'ui': {
        'currentDocId': None,
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
assert go['initial_state']['documents']['doc-1']['title'] == 'Recipe Collection'
assert go['initial_state']['comments'] == [], 'comments should start empty'
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
