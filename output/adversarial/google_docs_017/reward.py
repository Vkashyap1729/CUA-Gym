"""Reward for google_docs_017.

Task: In the "Press Release" document, replace every occurrence of the
placeholder "ACME" with "Globex" (title heading + both body mentions),
preserving surrounding text and HTML structure.

Scoring is a pure exact state check on documents[<press-release>].content.
The initial state has 3 "ACME" occurrences and 0 "Globex"; the completed
state has 0 "ACME" and 3 "Globex". Progressive credit is given per
correctly-replaced occurrence (1/3 each). No LLM judge is needed.
"""

import json
import urllib.request

BASE_URL = "https://cua-gym-google-docs.xlang.ai"

# The three placeholder occurrences that must be replaced.
TOTAL_OCCURRENCES = 3

# Structural fragments that must survive the find-and-replace (so a user
# who simply deletes/blanks the content does not get credit).
EXPECTED_FRAGMENTS = [
    "Launches Product",
    "today announced its new line",
    "CEO commented on the news",
]


def _read_sid():
    with open("/tmp/task_web_sid") as f:
        return f.read().strip()


def _fetch_state(sid):
    url = BASE_URL + "/go?sid=" + sid
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_press_release(documents):
    """Locate the "Press Release" document; prefer doc-1, fall back to title."""
    if not isinstance(documents, dict):
        return None
    doc = documents.get("doc-1")
    if isinstance(doc, dict) and "press release" in str(doc.get("title", "")).lower():
        return doc
    for d in documents.values():
        if isinstance(d, dict) and "press release" in str(d.get("title", "")).lower():
            return d
    # Last resort: doc-1 even if title not matched.
    return doc if isinstance(doc, dict) else None


def compute_reward():
    sid = _read_sid()
    data = _fetch_state(sid)
    current_state = data.get("current_state", {}) or {}

    documents = current_state.get("documents", {}) or {}
    doc = _find_press_release(documents)
    if not doc:
        return 0.0

    content = doc.get("content", "") or ""

    # Case-sensitive counts: "ACME" is an all-caps placeholder.
    acme_remaining = content.count("ACME")
    globex_count = content.count("Globex")

    # Number of occurrences correctly turned from ACME -> Globex.
    removed = max(0, TOTAL_OCCURRENCES - acme_remaining)
    replaced = min(removed, globex_count)
    replaced = min(replaced, TOTAL_OCCURRENCES)

    score = replaced / float(TOTAL_OCCURRENCES)

    # Guard against content deletion: if the surrounding text was destroyed,
    # the replacement was not done "preserving surrounding text/structure".
    if score > 0.0:
        intact = sum(1 for frag in EXPECTED_FRAGMENTS if frag in content)
        if intact < len(EXPECTED_FRAGMENTS):
            # Scale down proportionally to how much structure survived.
            score *= intact / float(len(EXPECTED_FRAGMENTS))

    # Full credit only when no placeholder remains and all three are replaced.
    if acme_remaining == 0 and globex_count >= TOTAL_OCCURRENCES:
        intact = sum(1 for frag in EXPECTED_FRAGMENTS if frag in content)
        if intact == len(EXPECTED_FRAGMENTS):
            score = 1.0

    return round(max(0.0, min(1.0, score)), 4)


if __name__ == "__main__":
    try:
        reward = compute_reward()
    except Exception as e:
        print("ERROR:", e)
        reward = 0.0
    print("REWARD:", reward)
