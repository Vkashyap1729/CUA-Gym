"""
Initial Setup: Make a copy of "Policy Handbook", then rename the copy to "Policy Handbook 2025".
Task ID: google_docs_028
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
# Per google_docs_mock schema. `documents` is a map keyed by doc ID.
# Task is NOT yet done: only the original "Policy Handbook" (doc-1) and "Org Chart"
# (doc-2) exist; no "Policy Handbook 2025" copy present.
state = {
    "currentUser": {
        "id": "user-1",
        "name": "Demo User",
        "email": "demo@example.com",
        "avatar": "https://picsum.photos/100/100?random=user1",
    },
    "users": [
        {
            "id": "user-1",
            "name": "Demo User",
            "email": "demo@example.com",
            "avatar": "https://picsum.photos/100/100?random=user1",
        },
        {
            "id": "user-2",
            "name": "Alice Chen",
            "email": "alice@example.com",
            "avatar": "https://picsum.photos/100/100?random=user2",
        },
        {
            "id": "user-3",
            "name": "Bob Smith",
            "email": "bob@example.com",
            "avatar": "https://picsum.photos/100/100?random=user3",
        },
    ],
    "documents": {
        "doc-1": {
            "id": "doc-1",
            "title": "Policy Handbook",
            "content": "<h1>Policy Handbook</h1><p>All company policies.</p>",
            "ownerId": "user-1",
            "starred": False,
            "created": "2025-01-15T10:00:00Z",
            "updated": "2025-02-18T14:30:00Z",
            "sharedWith": [],
            "linkSharing": {"enabled": False, "permission": "viewer"},
        },
        "doc-2": {
            "id": "doc-2",
            "title": "Org Chart",
            "content": "<h1>Org Chart</h1><p>Company organizational structure.</p>",
            "ownerId": "user-1",
            "starred": False,
            "created": "2025-01-20T09:00:00Z",
            "updated": "2025-02-10T11:00:00Z",
            "sharedWith": [],
            "linkSharing": {"enabled": False, "permission": "viewer"},
        },
    },
    "comments": [],
    "ui": {
        "currentDocId": None,
        "sidebarOpen": False,
        "sidebarTab": "comments",
        "shareDialogOpen": False,
        "findReplaceOpen": False,
        "viewMode": "editing",
        "zoom": 100,
        "documentListView": "grid",
        "searchQuery": "",
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
