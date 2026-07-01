"""
Golden Patch: Delete recurring "Old Weekly Sync" and create "Team Retro" on Mar 20 3-4 PM
Task ID: google_calendar_020
Domain: mock_websites
Mock: google_calendar
Changes: remove evt_110 ('Old Weekly Sync'); append new 'Team Retro' event (2026-03-20 15:00-16:00).
         evt_111 ('Team Standup') left untouched.
"""
import copy
import json

import requests

# --- Config ---
BASE_URL = 'https://cua-gym-google-calendar.xlang.ai'

# Read sid from initial_setup.py
with open('/tmp/task_web_sid') as f:
    sid = f.read().strip()

# --- Fetch current initial state ---
go = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=10).json()
state = copy.deepcopy(go['initial_state'])

# --- Apply ONLY the minimal changes the task requires ---
# 1) Delete the recurring "Old Weekly Sync" event (evt_110)
state['events'] = [e for e in state['events'] if e.get('id') != 'evt_110']

# 2) Append the new "Team Retro" event on March 20, 3 PM - 4 PM
state['events'].append({
    'id': 'evt_team_retro_1',
    'calendarId': 'c2',
    'title': 'Team Retro',
    'start': '2026-03-20T15:00:00.000Z',
    'end': '2026-03-20T16:00:00.000Z',
    'allDay': False,
    'location': '',
    'description': '',
    'guests': [],
    'color': '#33B679',
    'recurring': 'none',
    'reminders': [{'type': 'popup', 'minutes': 10}],
    'meetLink': '',
    'status': 'confirmed',
})

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
print('Verified: state_diff is non-empty')
