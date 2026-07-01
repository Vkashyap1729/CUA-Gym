"""Reward for gmail_007.

Task: Draft an email to the vendor procurement@acmesupplies.com requesting an
updated price quote for 200 office chairs, but DON'T send it yet.

Scores ONLY the task-introduced change: a new DRAFT (folder 'drafts' / entry in
the `drafts` array) addressed to procurement@acmesupplies.com, with a subject
about a price quote / office chairs and a body requesting an updated quote for
200 office chairs. Because the email must NOT be sent, any email in the 'sent'
folder addressed to the vendor is penalized. Touching the inbox distractors is
also penalized.

Initial state (drafts empty, no vendor draft) -> 0.0.
Golden state (correct draft, nothing sent, distractors intact) -> 1.0.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-gmail.xlang.ai"
VENDOR_EMAIL = "procurement@acmesupplies.com"


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _get_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _to_list(x):
    return x if isinstance(x, list) else []


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


def _to_vendor(item):
    return VENDOR_EMAIL in _addr_list(item.get("to")) if isinstance(item, dict) else False


def compute_reward():
    sid = _read_sid()
    data = _get_state(sid)
    current = data.get("current_state", {}) or {}
    diff = data.get("state_diff", {}) or {}

    emails = _to_list(current.get("emails"))
    drafts = _to_list(current.get("drafts"))

    # --- Locate the candidate draft addressed to the vendor. ---
    # Drafts may live in the top-level `drafts` array and/or as emails whose
    # folder is 'drafts'. Accept either.
    draft_candidates = [d for d in drafts if _to_vendor(d)]
    draft_candidates += [
        e
        for e in emails
        if str(e.get("folder", "")).lower() == "drafts" and _to_vendor(e)
    ]

    if not draft_candidates:
        # No draft to the vendor -> task not done (also covers "sent instead").
        print("No draft addressed to " + VENDOR_EMAIL + " found.")
        print("REWARD: 0.0")
        return

    draft = draft_candidates[0]
    score = 0.0

    # (1) A draft to the vendor exists. [0.35]
    score += 0.35

    # (2) Subject is about a price quote / office chairs. [0.15]  (exact keywords)
    subject = str(draft.get("subject", "")).lower()
    if ("quote" in subject or "quotation" in subject or "pricing" in subject
            or "price" in subject) or "chair" in subject:
        score += 0.15

    # (3) Body requests an updated quote for 200 office chairs. [0.30]
    body = str(draft.get("body", "")) or str(draft.get("snippet", ""))
    if body.strip():
        # JUSTIFICATION: Whether the draft's prose actually requests an *updated*
        # price quote for 200 office chairs is a subjective wording judgment that
        # exact string matching cannot reliably make; delegated to the LLM judge
        # (0.30 = 30% of total score, <=40% cap). All other criteria are exact
        # state checks.
        try:
            from reward_judge import call_llm_judge

            judge_score = call_llm_judge(
                task_instruction=(
                    "Draft an email to the vendor procurement@acmesupplies.com "
                    "requesting an updated price quote for 200 office chairs."
                ),
                success_criteria=(
                    "The draft email body requests an updated price quote from the "
                    "vendor for 200 office chairs. Score 1.0 if it clearly asks for "
                    "an updated/new quote AND mentions the quantity 200 office chairs; "
                    "score lower if the quantity (200), the item (office chairs), or "
                    "the request for an updated quote is missing, wrong, or ambiguous."
                ),
                state_excerpt=json.dumps(
                    {"subject": draft.get("subject"), "body": body},
                    ensure_ascii=False,
                ),
            )
            if isinstance(judge_score, (int, float)):
                score += 0.30 if judge_score >= 0.6 else 0.30 * float(judge_score)
        except Exception as exc:  # judge unavailable -> no partial credit for body
            print("LLM judge unavailable:", exc)

    # (4) The email was NOT sent: no email in the 'sent' folder to the vendor. [0.10]
    sent_to_vendor = [
        e
        for e in emails
        if str(e.get("folder", "")).lower() == "sent" and _to_vendor(e)
    ]
    if not sent_to_vendor:
        score += 0.10
    else:
        print("Email to vendor found in 'sent' folder (task said do NOT send).")
        # Strongly penalize sending, on top of withholding the 0.10 above.
        score -= 0.30

    # (5) Inbox distractors untouched. [0.10]
    modified = diff.get("modifiedEmails", {}) or {}
    deleted = diff.get("deletedEmails", []) or []
    tampered = False
    if modified:
        print("Pre-existing emails modified (over-action):", sorted(modified))
        tampered = True
    if deleted:
        print("Emails deleted (over-action):", deleted)
        tampered = True
    if not tampered:
        score += 0.10
    else:
        score -= 0.20

    score = max(0.0, min(1.0, score))
    print("REWARD: {:.1f}".format(score))


if __name__ == "__main__":
    compute_reward()
