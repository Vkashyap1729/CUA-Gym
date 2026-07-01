"""
Initial Setup: Clean up the "Archive" workspace: delete "Draft A" and "Draft B", but keep "Draft C".
Task ID: google_docs_025
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
# documents: doc-1 "Draft A", doc-2 "Draft B", doc-3 "Draft C", doc-4 "Master Index"
# (all owned by user-1). comment-1 on doc-1, comment-2 on doc-3.
# Task is NOT yet done: all four docs and both comments are present.
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
            'title': 'Draft A',
            'content': '<h1>Draft A</h1><p>First draft in the Archive workspace.</p>',
            'ownerId': 'user-1',
            'starred': False,
            'created': '2025-01-10T09:00:00Z',
            'updated': '2025-01-12T11:00:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
        'doc-2': {
            'id': 'doc-2',
            'title': 'Draft B',
            'content': '<h1>Draft B</h1><p>Second draft in the Archive workspace.</p>',
            'ownerId': 'user-1',
            'starred': False,
            'created': '2025-01-11T09:00:00Z',
            'updated': '2025-01-13T11:00:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
        'doc-3': {
            'id': 'doc-3',
            'title': 'Draft C',
            'content': '<h1>Draft C</h1><p>Third draft in the Archive workspace.</p>',
            'ownerId': 'user-1',
            'starred': False,
            'created': '2025-01-12T09:00:00Z',
            'updated': '2025-01-14T11:00:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
        'doc-4': {
            'id': 'doc-4',
            'title': 'Master Index',
            'content': '<h1>Master Index</h1><p>Index of the Archive workspace drafts.</p>',
            'ownerId': 'user-1',
            'starred': False,
            'created': '2025-01-09T09:00:00Z',
            'updated': '2025-01-15T11:00:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
    },
    'comments': [
        {
            'id': 'comment-1',
            'docId': 'doc-1',
            'userId': 'user-1',
            'content': 'This draft can probably be removed.',
            'resolved': False,
            'created': '2025-01-12T10:00:00Z',
            'quotedText': 'First draft',
            'replies': [],
        },
        {
            'id': 'comment-2',
            'docId': 'doc-3',
            'userId': 'user-1',
            'content': 'Keep this one as the final draft.',
            'resolved': False,
            'created': '2025-01-14T10:00:00Z',
            'quotedText': 'Third draft',
            'replies': [],
        },
    ],
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
assert set(go['initial_state']['documents'].keys()) == {'doc-1', 'doc-2', 'doc-3', 'doc-4'}, \
    'documents not set correctly'
assert len(go['initial_state']['comments']) == 2, 'comments not set correctly'
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
