"""Generate a DEMO benchmark run with full step-level trajectories (no VM/model).

Produces synthetic rollouts under output/benchmark/demo_run/ so the report app can
be seen populated: leaderboard, buckets, per-task detail, and Deep Dive
trajectories (SVG-placeholder screenshots + reasoning + actions). Real runs produce
the identical shape from actual VM screenshots + model reasoning.

  python scripts/benchmark/_demo.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.benchmark.analysis import write_reports  # noqa: E402

RUN = Path("output/benchmark/demo_run")
rng = random.Random(11)

MODELS = ["claude-opus", "claude-sonnet", "claude-haiku", "openai-cua"]
DOMAINS = {"gmail_001": "mock_websites", "calc_003": "libreoffice_calc",
           "gmail_007": "mock_websites", "gimp_002": "gimp",
           "slack_009": "mock_websites", "docs_005": "mock_websites"}
APP_LABEL = {"gmail_001": "Gmail", "gmail_007": "Gmail", "slack_009": "Slack",
             "docs_005": "Google Docs", "calc_003": "LibreOffice Calc", "gimp_002": "GIMP"}
ORACLE_OK = {t: (t != "docs_005") for t in DOMAINS}


def shot(app: str, step: int, tint: str) -> str:
    """Tiny SVG placeholder 'screenshot' as a self-contained data URI."""
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='320' height='200'>"
        f"<rect width='320' height='200' fill='#0e1526'/>"
        f"<rect width='320' height='26' fill='{tint}'/>"
        f"<text x='8' y='18' fill='#fff' font-family='sans-serif' font-size='13'>{app}</text>"
        f"<text x='160' y='120' fill='#8b93a3' font-family='sans-serif' font-size='40' "
        f"text-anchor='middle'>step {step}</text></svg>"
    )
    return "data:image/svg+xml;utf8," + quote(svg)


def traj_for(tid: str, outcome: str, reward):
    """Build a plausible step list for one rollout given its outcome."""
    app = APP_LABEL[tid]
    R = {
        "gmail_001": [("Click(1100, 210)", "Inbox loaded. Selecting the BargainHub newsletter."),
                      ("Click(60, 210)", "Opening the row actions menu."),
                      ("Click(180, 340)", "Choosing 'Move to Trash' for BargainHub."),
                      ("Click(1100, 260)", "Now the DealZone newsletter."),
                      ("Click(180, 390)", "Move to Trash for DealZone too.")],
        "calc_003": [("Click(300, 180)", "Spreadsheet open. Trying to select the data range."),
                     ("Drag(300,180,520,360)", "Highlighting the column to summarise."),
                     ("Click(640, 90)", "Looking for the formula/pivot control..."),
                     ("KeyPress(['ctrl','s'])", "Not sure this is right; trying to save state."),
                     ("Click(700, 120)", "Hunting for the right menu — can't find the pivot dialog.")],
        "gmail_007": [("Click(900, 240)", "Opening Marcus's thread."),
                      ("Click(120, 620)", "Clicking Reply."),
                      ("TypeText('Yes, Thursday 2 PM, 4th-floor room; I'll bring mockups.')",
                       "Confirming the three facts in the reply body."),
                      ("Click(200, 700)", "Sending.")],
        "gimp_002": [("Click(60, 300)", "Selecting the layer to adjust."),
                     ("Click(420, 40)", "Opening Colors menu."),
                     ("Click(440, 120)", "Choosing Brightness-Contrast."),
                     ("Drag(500,300,560,300)", "Nudging contrast up."),
                     ("Click(600, 420)", "Confirming.")],
        "slack_009": [("Click(240, 380)", "Finding the #design channel."),
                      ("Click(700, 900)", "Focusing the message box."),
                      ("TypeText('Posting the update as asked.')", "Typing the update."),
                      ("KeyPress(['enter'])", "Send.")],
        "docs_005": [("Click(1180, 90)", "Opening Share."),
                     ("TypeText('bob@example.com')", "Adding Bob."),
                     ("Click(980, 300)", "Setting permission to Commenter."),
                     ("Click(700, 520)", "Send — but the reward never confirms (task bug).")],
    }[tid]

    n = {"success": len(R), "partial": max(2, len(R) - 1), "truncated": len(R) + 1,
         "zero": max(2, len(R) - 2), "error": 2, "timeout": len(R)}[outcome]
    tint = {"mock_websites": "#b91c1c", "libreoffice_calc": "#166534",
            "gimp": "#7c3aed"}.get(DOMAINS[tid], "#1d4ed8")
    steps = []
    for i in range(n):
        act, rez = R[i % len(R)]
        if outcome == "truncated" and i >= len(R):
            act, rez = "Scroll(400, 400, dy=3)", "Still can't find the control — scrolling around."
        steps.append({"index": i, "actions": [act], "reasoning": rez, "screenshot": shot(app, i, tint)})
    # success/partial end with an explicit Done
    if outcome in ("success", "partial"):
        steps.append({"index": n, "actions": ["Done(success=True)"],
                      "reasoning": "Believe the task is complete.", "screenshot": shot(app, n, tint)})
    return steps


def mk_cell(passes, partials=0, trunc=0, err=0, to=0):
    out = [(1.0, "success")] * passes + [(round(rng.uniform(0.3, 0.7), 2), "partial")] * partials
    out += [(0.0, "truncated")] * trunc + [(None, "error")] * err + [(None, "timeout")] * to
    while len(out) < 5:
        out.append((0.0, "zero"))
    return out[:5]


PLAN = {
    "gmail_001": {m: mk_cell(5) for m in MODELS},                                    # too_easy
    "calc_003":  {m: mk_cell(0, trunc=4, err=1) for m in MODELS},                    # model_breaking
    "gmail_007": {"claude-opus": mk_cell(5), "claude-sonnet": mk_cell(4, 1),
                  "claude-haiku": mk_cell(1, 2, 1, 0, 1), "openai-cua": mk_cell(2, 1, 1, 1)},
    "gimp_002":  {"claude-opus": mk_cell(3, 1, 1), "claude-sonnet": mk_cell(1, 1, 2, 1),
                  "claude-haiku": mk_cell(0, 1, 3, 1), "openai-cua": mk_cell(0, 0, 4, 0, 1)},
    "slack_009": {"claude-opus": mk_cell(4, 1), "claude-sonnet": mk_cell(3, 1, 1),
                  "claude-haiku": mk_cell(2, 1, 2), "openai-cua": mk_cell(3, 1, 0, 1)},
    "docs_005":  {m: mk_cell(0, 2, 2, 1) for m in MODELS},                           # broken
}


def main():
    import shutil

    if RUN.exists():
        shutil.rmtree(RUN)
    (RUN / "rollouts").mkdir(parents=True)
    (RUN / "oracle").mkdir(parents=True)

    for t, ok in ORACLE_OK.items():
        (RUN / "oracle" / f"{t}.json").write_text(json.dumps(
            {"ok": ok, "reward_initial": 0.0, "reward_golden": 1.0 if ok else 0.6}))

    for tid, bym in PLAN.items():
        for m, seeds in bym.items():
            for s, (rwd, oc) in enumerate(seeds):
                steps = traj_for(tid, oc, rwd)
                dur = round(rng.uniform(25, 95) if oc == "success" else rng.uniform(60, 300), 1)
                (RUN / "rollouts" / f"{tid}__{m}__{s}.json").write_text(json.dumps({
                    "task_id": tid, "model": m, "seed": s, "app_type": DOMAINS[tid],
                    "instruction": f"({APP_LABEL[tid]} task)", "steps": steps,
                    "result": {"task_id": tid, "model": m, "seed": s, "reward": rwd,
                               "outcome": oc, "steps": len(steps),
                               "n_actions": len([a for st in steps for a in st["actions"]]),
                               "duration_s": dur,
                               "error": oc if oc in ("error", "timeout") else None,
                               "app_type": DOMAINS[tid]}}))

    rep = write_reports(RUN)
    print("buckets:", json.dumps(rep["buckets"]))
    print("wrote:", ", ".join(sorted(p.name for p in RUN.glob("*.html"))))


if __name__ == "__main__":
    main()
