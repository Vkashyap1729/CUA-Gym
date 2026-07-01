"""
Initial Setup: Rename "Untitled document" to "Sprint Retrospective Notes"
Task ID: google_docs_002
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
# Three documents owned by user-1. doc-1 is the (as-yet-unrenamed) "Untitled
# document" the task targets. doc-2 and doc-3 are distractors and must stay
# unchanged. The task is NOT yet done: doc-1.title is still "Untitled document".
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
            'title': 'Untitled document',
            'content': '<p></p>',
            'ownerId': 'user-1',
            'starred': False,
            'created': '2025-02-18T09:00:00Z',
            'updated': '2025-02-18T09:00:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
        'doc-2': {
            'id': 'doc-2',
            'title': 'Sprint Planning',
            'content': '<h1>Sprint Planning</h1><p>Goals for the upcoming sprint.</p>',
            'ownerId': 'user-1',
            'starred': False,
            'created': '2025-02-10T10:00:00Z',
            'updated': '2025-02-15T16:20:00Z',
            'sharedWith': [],
            'linkSharing': {'enabled': False, 'permission': 'viewer'},
        },
        'doc-3': {
            'id': 'doc-3',
            'title': 'Project Proposal',
            'content': '<h1>Project Proposal</h1><p>Overview of the proposed project.</p>',
            'ownerId': 'user-1',
            'starred': False,
            'created': '2025-01-20T11:30:00Z',
            'updated': '2025-02-05T13:45:00Z',
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
assert go['initial_state']['documents']['doc-1']['title'] == 'Untitled document'
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
