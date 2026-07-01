"""
Reward for gmail task gmail_011.

Task: Forward the project brief from Marcus to dana@corp.com, keep Marcus on cc,
and label the original as Work.

Scoring is progressive (0.0-1.0) and scores ONLY the task-introduced changes:
  1. A NEW email was sent (folder='sent', from the demo user) ......... 0.10
  2. The sent email is addressed TO dana@corp.com ................... 0.15
  3. The sent email keeps marcus@corp.com on cc .................... 0.15
  4. The sent email subject is a forward of the brief ('Fwd:' + orig)  0.15
  5. The original email_1 is labeled Work (l1) ..................... 0.20
  6. The forwarded body carries the original brief content (LLM) ... 0.25

New emails are identified by diffing current_state ids against initial_state ids
(robust; does not depend on the mock's state_diff being populated).

Over-action gate: the named distractors (email_2 'Coffee?', email_3, email_4)
must be untouched (folder/labels unchanged) and must NOT be forwarded. Any tampering
zeroes the score. A leftover draft of the forward (task left unsent) is penalized.
"""
import json
import urllib.request

from reward_judge import call_llm_judge

BASE_URL = "https://cua-gym-gmail.xlang.ai"

DANA = "dana@corp.com"
MARCUS = "marcus@corp.com"
WORK_LABEL = "l1"
ORIGINAL_ID = "email_1"
ORIGINAL_SUBJECT = "Project Atlas brief"
DISTRACTOR_IDS = ["email_2", "email_3", "email_4"]


def _email_addr(entry):
    """Lowercased email address of a from/to/cc entry."""
    if isinstance(entry, dict):
        return (entry.get("email") or "").strip().lower()
    return str(entry or "").strip().lower()


def _addr_list(entries):
    if not isinstance(entries, list):
        return []
    return [_email_addr(e) for e in entries]


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    with urllib.request.urlopen(BASE_URL + "/go?sid=" + sid, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    current = data.get("current_state", {}) or {}
    initial = data.get("initial_state", {}) or {}
    emails = current.get("emails", []) or []
    drafts = current.get("drafts", []) or []
    init_emails = initial.get("emails", []) or []

    by_id = {e.get("id"): e for e in emails if isinstance(e, dict)}
    init_by_id = {e.get("id"): e for e in init_emails if isinstance(e, dict)}
    init_ids = set(init_by_id.keys())

    # New emails = present now but not in the initial state.
    new_emails = [e for e in emails if isinstance(e, dict) and e.get("id") not in init_ids]

    # ---- Over-action gate: distractors must be untouched ----------------
    # email_1 may legitimately change (label + read); distractors may not.
    for did in DISTRACTOR_IDS:
        cur_e = by_id.get(did)
        init_e = init_by_id.get(did)
        if cur_e is None or init_e is None:
            continue
        if (cur_e.get("folder") or "") != (init_e.get("folder") or ""):
            print("OVER_ACTION: distractor %s folder changed" % did)
            print("REWARD: 0.0")
            return
        if set(cur_e.get("labels") or []) != set(init_e.get("labels") or []):
            print("OVER_ACTION: distractor %s labels changed" % did)
            print("REWARD: 0.0")
            return

    # Forwarding the wrong (distractor) email is a hard failure.
    for ne in new_emails:
        subj = (ne.get("subject") or "").lower()
        if "coffee" in subj:
            print("OVER_ACTION: forwarded the wrong (distractor) email: %s" % ne.get("id"))
            print("REWARD: 0.0")
            return

    score = 0.0

    # ---- Identify the sent forward email --------------------------------
    user_email = _email_addr((current.get("user") or {}).get("email"))
    sent_candidates = [e for e in new_emails if (e.get("folder") or "").lower() == "sent"]
    # Prefer the one that references the original brief.
    preferred = [
        e
        for e in sent_candidates
        if "atlas" in (e.get("subject") or "").lower()
        or "brief" in (e.get("subject") or "").lower()
    ]
    sent = (preferred or sent_candidates or [None])[0]

    if sent is not None:
        # 1. A new sent email exists, from the demo user
        if user_email and _email_addr(sent.get("from")) == user_email:
            score += 0.10
        else:
            # still credit existence of a sent email even if 'from' is odd
            score += 0.05

        to_addrs = _addr_list(sent.get("to"))
        cc_addrs = _addr_list(sent.get("cc"))

        # 2. addressed TO dana@corp.com
        if DANA in to_addrs:
            score += 0.15

        # 3. marcus kept on cc
        if MARCUS in cc_addrs:
            score += 0.15

        # 4. subject is a forward of the brief
        subj_l = (sent.get("subject") or "").lower()
        if "fwd" in subj_l and ORIGINAL_SUBJECT.lower() in subj_l:
            score += 0.15
        elif "fwd" in subj_l or ORIGINAL_SUBJECT.lower() in subj_l:
            score += 0.07

    # ---- 5. original email labeled Work (l1) ----------------------------
    orig = by_id.get(ORIGINAL_ID, {}) or {}
    orig_labels = orig.get("labels", []) or []
    if WORK_LABEL in orig_labels:
        score += 0.20

    # ---- 6. forwarded body carries the original brief (subjective) ------
    if sent is not None:
        success_criteria = (
            "The email body should be a forward that carries the ORIGINAL project "
            "brief content from Marcus Lee's 'Project Atlas brief' email. It should "
            "reproduce/quote the substantive brief text (not merely mention it). "
            "Give full credit only if the actual brief content is present in the body."
        )
        state_excerpt = json.dumps(
            {"subject": sent.get("subject"), "body": sent.get("body")},
            ensure_ascii=False,
        )
        # JUSTIFICATION: whether the forwarded body actually reproduces the original
        # brief text is a semantic/content judgement that cannot be an exact string
        # match (agents reword forward headers); delegate to the LLM judge. Capped at
        # 25% of the total score.
        judge = call_llm_judge(
            task_instruction="Forward the project brief from Marcus to dana@corp.com.",
            success_criteria=success_criteria,
            state_excerpt=state_excerpt,
        )
        try:
            judge = float(judge)
        except (TypeError, ValueError):
            judge = 0.0
        score += 0.25 * max(0.0, min(1.0, judge))

    # ---- Penalty: forward left as an unsent draft -----------------------
    leftover = False
    for d in drafts:
        subj = (d.get("subject") or "").lower()
        to_addrs = _addr_list(d.get("to"))
        if "atlas" in subj or "brief" in subj or DANA in to_addrs:
            leftover = True
            break
    if leftover:
        score = max(0.0, score - 0.15)

    score = max(0.0, min(1.0, score))
    print("REWARD: %.2f" % score)


if __name__ == "__main__":
    main()
