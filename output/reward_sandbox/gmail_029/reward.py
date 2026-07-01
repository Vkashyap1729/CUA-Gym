import json
import re
import sys

import requests

# --- Read sid ---
try:
    with open('/tmp/task_web_sid') as f:
        sid = f.read().strip()
except Exception:
    print('REWARD: 0.0')
    sys.exit(0)

BASE_URL = 'https://cua-gym-gmail.xlang.ai'

# --- Fetch state ---
try:
    data = requests.get(f'{BASE_URL}/go?sid={sid}', timeout=15).json()
except Exception:
    print('REWARD: 0.0')
    sys.exit(0)

initial = data.get('initial_state', {})
current = data.get('current_state', {})
state_diff = data.get('state_diff', {}) or {}

# --- Import LLM judge helper (pre-deployed by orchestrator to /tmp/) ---
sys.path.insert(0, '/tmp')
from reward_judge import call_llm_judge

CAROL_EMAIL = 'carol@company.com'
DAVE_EMAIL = 'dave@company.com'
THREAD_ID = 'thread_5'


def strip_html(text):
    if not text:
        return ''
    return re.sub(r'<[^>]+>', ' ', text)


def emails_of(state):
    return state.get('emails', []) or []


def find_reply(emails):
    """Find a sent email that replies to Carol in the same thread."""
    candidates = []
    for e in emails:
        if e.get('folder') != 'sent':
            continue
        recipients = [r.get('email', '').lower() for r in (e.get('to') or [])]
        if CAROL_EMAIL in recipients:
            candidates.append(e)
    # Prefer one in the correct thread
    for e in candidates:
        if e.get('threadId') == THREAD_ID:
            return e, candidates
    return (candidates[0] if candidates else None), candidates


def verify_task():
    total = 0.0

    cur_emails = emails_of(current)
    init_emails = emails_of(initial)
    init_ids = {e.get('id') for e in init_emails}

    reply, sent_to_carol = find_reply(cur_emails)

    # --- Component 1 (0.35) — a new email is sent to Carol ---
    if reply is not None and reply.get('id') not in init_ids:
        print('PASS: New sent email addressed to Carol (0.35 pts)')
        total += 0.35
    elif reply is not None:
        # A sent email to Carol exists but was already present initially
        print('FAIL: Sent email to Carol is not newly added')
    else:
        print('FAIL: No sent email addressed to Carol')

    # --- Component 2 (0.15) — reply belongs to the same thread (thread_5) ---
    if reply is not None and reply.get('threadId') == THREAD_ID:
        print('PASS: Reply is in the correct thread thread_5 (0.15 pts)')
        total += 0.15
    else:
        print('FAIL: Reply not in Carol\'s thread (thread_5)')

    # --- Component 3 (0.15) — subject looks like a reply to the design review ---
    if reply is not None:
        subj = (reply.get('subject') or '').lower()
        if 'design review' in subj or subj.startswith('re:'):
            print('PASS: Subject is an appropriate reply subject (0.15 pts)')
            total += 0.15
        else:
            print('FAIL: Subject does not match a reply to the design review')
    else:
        print('FAIL: No reply to evaluate subject')

    # --- Component 4 (0.35) — body affirmatively confirms attendance (LLM judge) ---
    # JUSTIFICATION: Confirming attendance can be phrased in unlimited ways
    # ("Yes, I'll be there", "Count me in", "Confirming I'll attend"). There is no
    # single correct wording, so semantic judgement is required here.
    if reply is not None:
        body_text = strip_html(reply.get('body') or '')
        try:
            llm_score = call_llm_judge(
                task_instruction=(
                    'Reply to Carol confirming you will attend the Thursday 2pm design review.'
                ),
                success_criteria=(
                    'The reply body clearly and affirmatively confirms that the sender WILL '
                    'attend the Thursday design review (an acceptance/yes). A decline, a '
                    'maybe, or an unrelated message does NOT satisfy this.'
                ),
                state_excerpt=json.dumps({
                    'subject': reply.get('subject'),
                    'body': body_text,
                }),
            )
        except Exception as e:
            llm_score = 0.0
            print(f'ERROR: Component 4 LLM judge — {e}')
        total += 0.35 * llm_score
        print(f'LLM JUDGE: reply confirms attendance — {0.35 * llm_score:.2f} pts')
    else:
        print('FAIL: No reply body to evaluate')

    # --- Over-action penalty — distractor email_2 (Dave) must be untouched ---
    penalty_ok = True

    # email_2 must still exist, in inbox, unmodified
    dave_email_obj = next((e for e in cur_emails if e.get('id') == 'email_2'), None)
    if dave_email_obj is None:
        print('PENALTY: distractor email_2 was deleted/altered')
        penalty_ok = False
    elif dave_email_obj.get('folder') != 'inbox':
        print('PENALTY: distractor email_2 was moved out of inbox')
        penalty_ok = False

    # No reply/new email should have been sent to Dave
    for e in cur_emails:
        if e.get('id') in init_ids:
            continue
        recipients = [r.get('email', '').lower() for r in (e.get('to') or [])]
        if DAVE_EMAIL in recipients:
            print('PENALTY: an unexpected new email was sent to Dave')
            penalty_ok = False
            break

    if not penalty_ok:
        print('Over-action detected — zeroing score')
        total = 0.0

    final = max(0.0, min(total, 1.0))
    print(f'\nScore: {total}/1.0')
    print(f'REWARD: {final}')
    return final


verify_task()
