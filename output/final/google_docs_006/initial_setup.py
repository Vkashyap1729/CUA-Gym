"""
Initial Setup: Unstar the "Vacation Itinerary" document
Task ID: google_docs_006
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
# documents: doc-1 "Vacation Itinerary" (user-1, starred=true) -> task NOT yet done,
#            doc-2 "Expense Report" (user-1, starred=true) distractor stays starred,
#            doc-3 "Reading List" (user-1, starred=false) distractor stays unstarred.
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
            'title': 'Vacation Itinerary',
            'content': '<h1>Vacation Itinerary</h1><p>Day 1: Arrival and check-in.</p>'
                       '<p>Day 2: City tour.</p><p>Day 3: Departure.</p>',
            'ownerId': 'user-1',
            'starred': True,
            'created': '2025-01-10T09:00:00Z',
            'updated': '2025-02-14T11:20:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
        'doc-2': {
            'id': 'doc-2',
            'title': 'Expense Report',
            'content': '<h1>Expense Report</h1><p>Q1 travel and lodging expenses.</p>',
            'ownerId': 'user-1',
            'starred': True,
            'created': '2025-01-12T10:30:00Z',
            'updated': '2025-02-15T16:45:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
        'doc-3': {
            'id': 'doc-3',
            'title': 'Reading List',
            'content': '<h1>Reading List</h1><p>Books to read this year.</p>',
            'ownerId': 'user-1',
            'starred': False,
            'created': '2025-01-20T08:15:00Z',
            'updated': '2025-02-10T13:00:00Z',
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
    timeout=30,
)
assert resp.status_code == 200, f'State injection failed: {resp.text}'
print(f'State injected: sid={sid}')

# --- Verify ---
go = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
assert go['initial_state'] is not None, 'initial_state is None after injection'
assert go['initial_state']['documents']['doc-1']['starred'] is True, 'doc-1 should start starred'
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
