"""Reward for gmail_006.

Task: Reply to Priya's email about the design review and let her know the user
can make the 3pm slot on Thursday.

Scores ONLY the task-introduced change: a new email in the 'sent' folder,
addressed to Priya (priya@studio.design), on threadId 'thread_1', with a subject
referencing the design review, and a body confirming availability for the 3pm
Thursday slot. Over-action (touching the original or distractor emails, or
creating a draft) is penalized.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"
PRIYA_EMAIL = "priya@studio.design"
ORIGINAL_ID = "email_1"
THREAD_ID = "thread_1"
USER_EMAIL = "demo@example.com"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _get_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _to_list(emails):
    return emails if isinstance(emails, list) else []


def _addr_list(field):
    """Normalize a to/cc field into a list of lowercased email strings."""
    out = []
    if isinstance(field, list):
        for r in field:
            if isinstance(r, dict) and r.get("email"):
                out.append(str(r["email"]).strip().lower())
            elif isinstance(r, str):
                out.append(r.strip().lower())
    return out


def compute_reward():
    sid = _read_sid()
    data = _get_state(sid)
    current = data.get("current_state", {}) or {}
    diff = data.get("state_diff", {}) or {}

    emails = _to_list(current.get("emails"))
    drafts = _to_list(current.get("drafts"))

    # --- Locate the candidate reply: a sent email addressed to Priya. ---
    sent_to_priya = [
        e
        for e in emails
        if isinstance(e, dict)
        and str(e.get("folder", "")).lower() == "sent"
        and PRIYA_EMAIL in _addr_list(e.get("to"))
    ]

    if not sent_to_priya:
        # No reply was sent -> task not done.
        print("No sent email addressed to Priya found.")
        print("REWARD: 0.0")
        return

    # Prefer a candidate already on thread_1, else the first.
    reply = next(
        (e for e in sent_to_priya if str(e.get("threadId", "")) == THREAD_ID),
        sent_to_priya[0],
    )

    score = 0.0

    # (1) A reply email exists in the sent folder to Priya. [0.20]
    score += 0.20

    # (2) Sent from the demo user. [0.15]
    from_email = ""
    if isinstance(reply.get("from"), dict):
        from_email = str(reply["from"].get("email", "")).strip().lower()
    if from_email == USER_EMAIL:
        score += 0.15

    # (3) Reply is threaded onto the original conversation. [0.15]
    if str(reply.get("threadId", "")) == THREAD_ID:
        score += 0.15

    # (4) Subject references the design review. [0.20]
    subject = str(reply.get("subject", "")).lower()
    if "design review" in subject or ("design" in subject and "review" in subject):
        score += 0.20

    # (5) Body confirms availability for the 3pm Thursday slot. [0.30]
    body = str(reply.get("body", "")) or str(reply.get("snippet", ""))
    if body.strip():
        # JUSTIFICATION: Whether the reply's prose actually confirms availability
        # for the 3pm Thursday slot is a subjective wording judgment that exact
        # string matching cannot reliably make; delegated to the LLM judge
        # (0.30 = 30% of total score, <=40% cap).
        try:
            from reward_judge import call_llm_judge

            judge_score = call_llm_judge(
                task_instruction=(
                    "Reply to Priya's email about the design review and let her know "
                    "you can make the 3pm slot on Thursday."
                ),
                success_criteria=(
                    "The email body clearly confirms/accepts that the sender is "
                    "available for the 3pm slot on Thursday for the design review. "
                    "Score 1.0 if it plainly agrees to 3pm Thursday; score lower if "
                    "the day or time is missing, wrong, or ambiguous."
                ),
                state_excerpt=json.dumps(
                    {"subject": reply.get("subject"), "body": body},
                    ensure_ascii=False,
                ),
            )
            # call_llm_judge returns a float in [0.0, 1.0]. Threshold so a clearly
            # correct body earns the full sub-score; give partial credit otherwise.
            if isinstance(judge_score, (int, float)):
                score += 0.30 if judge_score >= 0.6 else 0.30 * float(judge_score)
        except Exception as exc:  # judge unavailable -> no partial credit for body
            print("LLM judge unavailable:", exc)

    # --- Over-action penalties. ---
    modified = diff.get("modifiedEmails", {}) or {}
    deleted = diff.get("deletedEmails", []) or []

    # Original email_1 must be unchanged (a benign read-status flip is tolerated).
    orig_changes = modified.get(ORIGINAL_ID, {}) or {}
    orig_bad = {k for k in orig_changes if k != "read"}
    if orig_bad:
        print("Original email modified beyond read status:", sorted(orig_bad))
        score -= 0.30

    # Distractor / other existing emails must be untouched. The reply is a new
    # email (in newEmails), so any modifiedEmails entry other than email_1 is
    # over-action.
    other_modified = [eid for eid in modified if eid != ORIGINAL_ID]
    if other_modified:
        print("Distractor/other emails modified:", other_modified)
        score -= 0.30

    if deleted:
        print("Emails deleted (over-action):", deleted)
        score -= 0.30

    # No draft should have been created for this reply.
    draft_to_priya = [
        d
        for d in drafts
        if isinstance(d, dict) and PRIYA_EMAIL in _addr_list(d.get("to"))
    ]
    if draft_to_priya:
        print("A draft to Priya was created (over-action).")
        score -= 0.20

    score = max(0.0, min(1.0, score))
    print("REWARD: {:.1f}".format(score))


if __name__ == "__main__":
    compute_reward()
