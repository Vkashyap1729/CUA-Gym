"""
Initial Setup: Star the document titled "Q3 Marketing Plan"
Task ID: google_docs_001
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
# Three documents owned by user-1. The task target "Q3 Marketing Plan" (doc-1)
# starts UNSTARRED (task not yet done -> fresh reward must be 0.0).
# Distractors: doc-2 already starred (must STAY starred), doc-3 unstarred
# (must STAY unstarred).
user_1 = {
    'id': 'user-1',
    'name': 'Demo User',
    'email': 'demo@example.com',
    'avatar': 'https://picsum.photos/100/100?random=user1',
}
user_2 = {
    'id': 'user-2',
    'name': 'Alice Chen',
    'email': 'alice@example.com',
    'avatar': 'https://picsum.photos/100/100?random=user2',
}
user_3 = {
    'id': 'user-3',
    'name': 'Bob Smith',
    'email': 'bob@example.com',
    'avatar': 'https://picsum.photos/100/100?random=user3',
}

state = {
    'currentUser': user_1,
    'users': [user_1, user_2, user_3],
    'documents': {
        'doc-1': {
            'id': 'doc-1',
            'title': 'Q3 Marketing Plan',
            'content': '<h1>Q3 Marketing Plan</h1><p>Campaign goals and budget for Q3.</p>',
            'ownerId': 'user-1',
            'starred': False,
            'created': '2025-01-15T10:00:00Z',
            'updated': '2025-02-18T14:30:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
        'doc-2': {
            'id': 'doc-2',
            'title': 'Budget Forecast',
            'content': '<h1>Budget Forecast</h1><p>Projected revenue and expenses.</p>',
            'ownerId': 'user-1',
            'starred': True,
            'created': '2025-01-10T09:00:00Z',
            'updated': '2025-02-12T11:00:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
        'doc-3': {
            'id': 'doc-3',
            'title': 'Team Roster',
            'content': '<h1>Team Roster</h1><p>Current team members and roles.</p>',
            'ownerId': 'user-1',
            'starred': False,
            'created': '2025-01-05T08:00:00Z',
            'updated': '2025-02-08T16:45:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
    },
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
    timeout=30
)
assert resp.status_code == 200, f'State injection failed: {resp.text}'
print(f'State injected: sid={sid}')

# --- Verify ---
go = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go['initial_state'] is not None, 'initial_state is None after injection'
assert go['initial_state']['documents']['doc-1']['starred'] is False, \
    'doc-1 should start unstarred (task not yet done)'
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
