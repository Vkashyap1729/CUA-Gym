"""
Reward for gmail task gmail_032.

TASK: Save a DRAFT email to ana@company.com and paul@company.com with subject
'Expense report reminder' reminding them the report is due Friday. Do NOT send it.

Scores ONLY the task-introduced change (a new draft). Progressive 0.0-1.0.
- initial state (drafts: []) -> 0.0
- fully-completed state       -> 1.0
Penalizes over-action: the email must NOT be sent (no new folder:'sent' email),
and the pre-existing distractor email_1 must be untouched.
"""
import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"

REQUIRED_RECIPIENTS = {"ana@company.com", "paul@company.com"}
EXPECTED_SUBJECT = "expense report reminder"

# Score weights (sum to 1.0)
W_DRAFT_EXISTS = 0.25   # a new draft was saved
W_RECIPIENTS = 0.25     # both finance-team recipients present
W_SUBJECT = 0.20        # subject exactly matches
W_BODY = 0.30           # body reminds report is due Friday (LLM judge <= 40%)


def _norm(s):
    return (s or "").strip().lower()


def _collect_emails(obj):
    """Return normalized recipient emails from a to/cc field which may be a list
    of {email} dicts, a list of strings, or a comma/semicolon-separated string."""
    out = []
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                out.append(_norm(item.get("email")))
            elif isinstance(item, str):
                out.append(_norm(item))
    elif isinstance(obj, str):
        for part in obj.replace(";", ",").split(","):
            out.append(_norm(part))
    return [e for e in out if e]


def main():
    with open("/tmp/task_web_sid") as f:
        sid = f.read().strip()

    with urllib.request.urlopen(BASE_URL + "/go?sid=" + sid, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current_state", {}) or {}
    diff = data.get("state_diff", {}) or {}

    drafts = [d for d in (current.get("drafts") or []) if isinstance(d, dict)]
    emails = [e for e in (current.get("emails") or []) if isinstance(e, dict)]

    # -------- Over-action penalties (hard gates) --------
    # Nothing must be SENT: the task explicitly says keep it a draft.
    if any(_norm(e.get("folder")) == "sent" for e in emails):
        print("PENALTY: an email was sent (folder='sent'); task requires a DRAFT only.")
        print("REWARD: 0.0")
        return

    # The distractor email_1 must remain untouched.
    modified = diff.get("modifiedEmails", {}) or {}
    deleted = diff.get("deletedEmails", []) or []
    if "email_1" in modified:
        print("PENALTY: distractor email_1 was modified.")
        print("REWARD: 0.0")
        return
    if "email_1" in deleted:
        print("PENALTY: distractor email_1 was deleted.")
        print("REWARD: 0.0")
        return

    if not drafts:
        print("No draft saved.")
        print("REWARD: 0.0")
        return

    # -------- Identify and score the task-introduced draft --------
    def score_draft(d):
        s = 0.0
        recipients = set(_collect_emails(d.get("to")))
        subject = _norm(d.get("subject"))
        body = d.get("body") or d.get("snippet") or ""

        # (1) A draft exists / is a real compose (has some content).
        if d.get("to") or d.get("subject") or body:
            s += W_DRAFT_EXISTS

        # (2) Recipients: both finance-team members present (proportional).
        matched = REQUIRED_RECIPIENTS & recipients
        s += W_RECIPIENTS * (len(matched) / len(REQUIRED_RECIPIENTS))

        # (3) Subject exactly 'Expense report reminder' (partial for substring).
        if subject == EXPECTED_SUBJECT:
            s += W_SUBJECT
        elif EXPECTED_SUBJECT in subject:
            s += W_SUBJECT * 0.5

        # (4) Body reminds them the report is due Friday. (LLM judge, <= 40%)
        if body:
            # JUSTIFICATION: whether the free-text body actually reminds the
            # finance team that the (expense) report is due Friday is a subjective
            # wording check that cannot be verified by exact state matching.
            from reward_judge import call_llm_judge

            body_score = call_llm_judge(
                "Save a draft email reminding the finance team their expense "
                "report is due Friday.",
                "The email body reminds the recipients that the (expense) report "
                "is due on Friday. Full credit only if it clearly conveys the "
                "report is due Friday.",
                "Draft subject: " + str(d.get("subject", "")) + "\n"
                "Draft body: " + str(body),
            )
            s += W_BODY * float(body_score)
        return s

    score = max(score_draft(d) for d in drafts)
    score = max(0.0, min(1.0, score))
    print("REWARD: " + str(round(score, 4)))


if __name__ == "__main__":
    main()
