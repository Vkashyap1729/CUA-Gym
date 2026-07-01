"""Reward for gmail_017: Reply to Bob's invoice email (#2291) saying payment by Friday.

Progressive 0.0-1.0. Scores ONLY the task-introduced change: a new SENT reply to
Bob Lee <bob@vendor.io> in thread_bob, subject 'Re:' referencing invoice/2291, body
communicating payment will be sent by Friday. Penalizes over-action on the distractor
(email_2 from Priya / invoice #2288) and requires the original email_1 to be preserved.
"""

import json
import urllib.request

from reward_judge import call_llm_judge

BASE_URL = "https://cua-gym-gmail.xlang.ai"

BOB_EMAIL = "bob@vendor.io"
PRIYA_EMAIL = "priya@vendor.io"

TASK = "Reply to Bob's invoice email letting him know payment will be sent by Friday."


def _get_state():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _emails(state):
    return (state or {}).get("emails", []) or []


def _to_emails(email):
    return [(r.get("email") or "").lower() for r in (email.get("to") or [])]


def main():
    data = _get_state()
    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}

    cur_emails = _emails(current)
    init_ids = {e.get("id") for e in _emails(initial)}

    # -------- locate the newly-sent reply to Bob --------
    def is_sent_reply_to_bob(e):
        if e.get("folder") != "sent":
            return False
        frm = (e.get("from") or {}).get("email", "").lower()
        if frm != "demo@example.com":
            return False
        return BOB_EMAIL in _to_emails(e)

    reply = None
    for e in cur_emails:
        if e.get("id") in init_ids:  # only newly-added emails
            continue
        if is_sent_reply_to_bob(e):
            reply = e
            break

    score = 0.0

    # (1) A sent reply addressed to Bob exists  -- 0.25
    if reply is None:
        print("No sent reply to Bob found -> task not done")
        print("REWARD: 0.0")
        return
    score += 0.25

    subject = reply.get("subject") or ""
    subj_l = subject.lower().strip()
    body = reply.get("body") or ""

    # (2) Subject is a reply ('Re:') referencing invoice #2291 (not distractor 2288) -- 0.20
    is_reply_subject = subj_l.startswith("re:")
    refs_invoice = ("invoice" in subj_l) or ("2291" in subj_l)
    wrong_invoice = "2288" in subj_l
    if is_reply_subject and refs_invoice and not wrong_invoice:
        score += 0.20
    elif is_reply_subject:
        score += 0.10  # partial: a reply, but subject doesn't clearly cite 2291

    # (3) Correct thread threading  -- 0.15
    if reply.get("threadId") == "thread_bob":
        score += 0.15

    # (4) Body communicates payment will be sent by Friday  -- 0.30 (LLM judge)
    body_text = (subject + "\n" + body).strip()
    if body_text:
        # JUSTIFICATION: Whether a free-text reply communicates "payment will be sent
        # by Friday" is a semantic/subjective judgment that no exact state check can
        # capture; delegated to the LLM judge (weighted at 30% <= 40% of total score).
        judge_score = call_llm_judge(
            task_instruction=TASK,
            success_criteria=(
                "The reply must clearly communicate a commitment that payment for the "
                "invoice will be sent/paid by Friday. Score 1.0 only if it states "
                "payment will be sent by Friday; partial credit if payment timing is "
                "mentioned but vague; 0.0 if it does not commit to paying by Friday."
            ),
            state_excerpt="Subject: " + subject + "\n\nBody:\n" + body,
        )
        score += 0.30 * float(judge_score)

    # (5) No over-action: distractor & originals preserved  -- 0.10 (gate)
    over_action = False

    # 5a. email_1 (Bob's original) must still exist, in inbox
    orig_bob = next((e for e in cur_emails if e.get("id") == "email_1"), None)
    if orig_bob is None or orig_bob.get("folder") != "inbox":
        over_action = True

    # 5b. email_2 (Priya distractor) unchanged: still inbox, and no reply sent to Priya
    orig_priya = next((e for e in cur_emails if e.get("id") == "email_2"), None)
    if orig_priya is None or orig_priya.get("folder") != "inbox":
        over_action = True
    for e in cur_emails:
        if e.get("id") in init_ids:
            continue
        if e.get("folder") == "sent" and PRIYA_EMAIL in _to_emails(e):
            over_action = True  # replied to the distractor invoice

    if not over_action:
        score += 0.10
    else:
        score = min(score, 0.5)  # over-action is a real mistake; cap below completion
        print("Over-action detected (distractor touched or original altered)")

    score = round(max(0.0, min(1.0, score)), 2)
    print("REWARD: " + str(score))


if __name__ == "__main__":
    main()
