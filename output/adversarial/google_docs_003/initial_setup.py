"""
Initial Setup: Delete the document called "Old Draft v1"
Task ID: google_docs_003
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
# Three documents owned by user-1; doc-1 "Old Draft v1" is the one to delete.
# comment-1 belongs to doc-1 (must disappear with the doc), comment-2 belongs to doc-2 (must remain).
state = {
    'currentUser': {
        'id': 'user-1',
        'name': 'Demo User',
        'email': 'demo@example.com',
        'avatar': 'https://picsum.photos/100/100?random=user1',
    },
    'users': [
        {'id': 'user-1', 'name': 'Demo User', 'email': 'demo@example.com', 'avatar': 'https://picsum.photos/100/100?random=user1'},
        {'id': 'user-2', 'name': 'Alice Chen', 'email': 'alice@example.com', 'avatar': 'https://picsum.photos/100/100?random=user2'},
        {'id': 'user-3', 'name': 'Bob Smith', 'email': 'bob@example.com', 'avatar': 'https://picsum.photos/100/100?random=user3'},
    ],
    'documents': {
        'doc-1': {
            'id': 'doc-1',
            'title': 'Old Draft v1',
            'content': '<h1>Old Draft v1</h1><p>This is an outdated draft that is no longer needed.</p>',
            'ownerId': 'user-1',
            'starred': False,
            'created': '2025-01-10T09:00:00Z',
            'updated': '2025-01-12T11:00:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
        'doc-2': {
            'id': 'doc-2',
            'title': 'Old Draft v2',
            'content': '<h1>Old Draft v2</h1><p>A second draft revision with more details.</p>',
            'ownerId': 'user-1',
            'starred': False,
            'created': '2025-01-15T09:00:00Z',
            'updated': '2025-01-18T16:30:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
        'doc-3': {
            'id': 'doc-3',
            'title': 'Final Report',
            'content': '<h1>Final Report</h1><p>The finalized report ready for submission.</p>',
            'ownerId': 'user-1',
            'starred': True,
            'created': '2025-02-01T10:00:00Z',
            'updated': '2025-02-20T14:45:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
    },
    'comments': [
        {
            'id': 'comment-1',
            'docId': 'doc-1',
            'userId': 'user-2',
            'content': 'This draft looks outdated, should we remove it?',
            'resolved': False,
            'created': '2025-01-11T10:00:00Z',
            'quotedText': 'outdated draft',
            'replies': [],
        },
        {
            'id': 'comment-2',
            'docId': 'doc-2',
            'userId': 'user-3',
            'content': 'Nice improvements in this version.',
            'resolved': False,
            'created': '2025-01-16T13:00:00Z',
            'quotedText': 'second draft revision',
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
assert 'doc-1' in go['initial_state']['documents'], 'doc-1 missing from initial state'
assert 'doc-2' in go['initial_state']['documents'], 'doc-2 missing from initial state'
assert 'doc-3' in go['initial_state']['documents'], 'doc-3 missing from initial state'
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
