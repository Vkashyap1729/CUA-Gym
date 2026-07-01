"""Reward for gmail_019.

Task: Compose and send a new email to hr@company.com requesting Friday off for a
doctor's appointment.

Scoring (progressive, 0.0-1.0), scores ONLY the task-introduced change:
  0.30  a new email exists in folder 'sent' addressed to hr@company.com
  0.10  that email is from the current user (Demo User / demo@example.com)
  0.20  subject indicates a time-off / leave / day-off request (exact keyword check)
  0.40  body requests Friday off for a doctor's appointment (LLM judge, <=40%)

Over-action penalties (subtractive, floored at 0.0):
  -0.20  distractor email_1 modified or deleted
  -0.20  distractor email_2 modified or deleted
  -0.10  a draft left behind
"""

import re
import urllib.request
import json

BASE_URL = "https://cua-gym-gmail.xlang.ai"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _emails_to(email_obj):
    """Return lowercased set of recipient emails from a 'to' list."""
    out = set()
    for r in email_obj.get("to", []) or []:
        if isinstance(r, dict) and r.get("email"):
            out.add(r["email"].strip().lower())
    return out


def _strip_html(html):
    return re.sub(r"<[^>]+>", " ", html or "").replace("&nbsp;", " ")


def compute_reward():
    sid = _read_sid()
    data = _fetch(sid)
    current = data.get("current_state", {}) or {}
    diff = data.get("state_diff", {}) or {}

    emails = current.get("emails", []) or []
    user = current.get("user", {}) or {}
    user_email = (user.get("email") or "demo@example.com").strip().lower()

    # --- locate the task-introduced sent email to hr@company.com ---
    HR = "hr@company.com"
    sent_candidates = [
        e
        for e in emails
        if (e.get("folder") == "sent") and (HR in _emails_to(e))
    ]

    score = 0.0

    if not sent_candidates:
        # Nothing sent to HR -> task not done. This is the initial-state path.
        print("No sent email addressed to hr@company.com found.")
        return 0.0

    # Prefer a candidate that is also flagged as newly-added, if diff is present.
    new_ids = set(diff.get("newEmails", []) or [])
    chosen = None
    for e in sent_candidates:
        if e.get("id") in new_ids:
            chosen = e
            break
    if chosen is None:
        chosen = sent_candidates[0]

    # 0.30 -- new sent email addressed to hr@company.com
    score += 0.30
    print("Found sent email to hr@company.com (+0.30)")

    # 0.10 -- from the current user
    frm = chosen.get("from", {}) or {}
    from_email = (frm.get("email") or "").strip().lower()
    if from_email == user_email:
        score += 0.10
        print("Sender is the current user (+0.10)")
    else:
        print(f"Sender {from_email!r} != current user {user_email!r} (+0.0)")

    # 0.20 -- subject indicates a time-off / leave / day-off request
    subject = (chosen.get("subject") or "").lower()
    subj_keywords = [
        "time off",
        "time-off",
        "day off",
        "day-off",
        "off",
        "leave",
        "absence",
        "absent",
        "pto",
        "vacation",
        "out of office",
        "ooo",
        "friday",
        "doctor",
        "appointment",
    ]
    if any(k in subject for k in subj_keywords):
        score += 0.20
        print(f"Subject indicates a time-off request (+0.20): {chosen.get('subject')!r}")
    else:
        print(f"Subject does not indicate a time-off request (+0.0): {chosen.get('subject')!r}")

    # 0.40 -- body requests Friday off for a doctor's appointment (LLM judge)
    body_text = _strip_html(chosen.get("body", "")).strip()
    full_subject = chosen.get("subject") or ""
    # JUSTIFICATION: whether an email body genuinely (a) requests to take Friday off
    # and (b) attributes the reason to a doctor's appointment is a subjective wording
    # judgement that no exact state check can capture; capped at 40% of the score.
    from reward_judge import call_llm_judge

    task_instruction = (
        "Compose and send a new email to hr@company.com requesting Friday off for a "
        "doctor's appointment."
    )
    success_criteria = (
        "The email text must BOTH (1) request/ask to take Friday off (a specific day "
        "away from work), AND (2) state that the reason is a doctor's appointment "
        "(medical appointment). Score 1.0 only if both elements are clearly present. "
        "Score 0.5 if only one element is present. Score 0.0 if the text is empty, "
        "unrelated, or requests neither Friday off nor mentions a doctor's appointment."
    )
    state_excerpt = f"SUBJECT: {full_subject}\nBODY: {body_text}"
    try:
        judge_score = float(call_llm_judge(task_instruction, success_criteria, state_excerpt))
    except Exception as ex:
        judge_score = 0.0
        print(f"LLM judge error: {ex}")
    judge_score = max(0.0, min(1.0, judge_score))
    # Band the judge output so a clearly-correct body earns the full 0.40 (both
    # elements present), a half-right body 0.20, and an empty/unrelated body 0.0.
    if judge_score >= 0.8:
        body_points = 0.40
    elif judge_score >= 0.4:
        body_points = 0.20
    else:
        body_points = 0.0
    score += body_points
    print(f"Body judge score={judge_score} -> +{body_points}")

    # --- over-action penalties: distractors must be untouched, no draft left ---
    modified = diff.get("modifiedEmails", {}) or {}
    deleted = set(diff.get("deletedEmails", []) or [])

    for did in ("email_1", "email_2"):
        if did in modified or did in deleted:
            score -= 0.20
            print(f"PENALTY: distractor {did} was modified/deleted (-0.20)")

    drafts = current.get("drafts", []) or []
    if len(drafts) > 0:
        score -= 0.10
        print(f"PENALTY: {len(drafts)} draft(s) left behind (-0.10)")

    score = max(0.0, min(1.0, score))
    return round(score, 2)


if __name__ == "__main__":
    r = compute_reward()
    print(f"REWARD: {r}")
