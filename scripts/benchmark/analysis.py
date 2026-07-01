"""Analysis: rollout traces -> metrics -> buckets -> report.{json,md,html}.

Reads output/benchmark/<run_id>/rollouts/*.json + oracle/*.json and produces:
  - report.json : machine-readable full metrics (cells, models, tasks, buckets)
  - report.md   : human summary
  - report.html : shareable dashboard

This is what turns raw episodes into "how many times each model failed, broken
down by failure type" + the per-task difficulty buckets.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.benchmark.metrics import (  # noqa: E402
    Bucket,
    Outcome,
    RolloutResult,
    classify_task,
    summarize_cell,
    summarize_model,
)


def load_rollouts(run_dir: Path) -> list[RolloutResult]:
    out = []
    for f in sorted((run_dir / "rollouts").glob("*.json")):
        trace = json.loads(f.read_text())
        r = trace.get("result") or {}
        if not r:
            continue
        out.append(RolloutResult(
            task_id=r["task_id"], model=r["model"], seed=r["seed"],
            reward=r["reward"], outcome=Outcome(r["outcome"]),
            steps=r.get("steps", 0), n_actions=r.get("n_actions", 0),
            duration_s=r.get("duration_s", 0.0), error=r.get("error"),
            app_type=r.get("app_type", "unknown"),
        ))
    return out


def load_oracle(run_dir: Path) -> dict:
    res = {}
    for f in sorted((run_dir / "oracle").glob("*.json")):
        res[f.stem] = json.loads(f.read_text())
    return res


def analyze(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    rollouts = load_rollouts(run_dir)
    oracle = load_oracle(run_dir)

    models = sorted({r.model for r in rollouts})
    task_ids = sorted({r.task_id for r in rollouts})

    # Per-(task, model) cells.
    cells = {}
    for tid in task_ids:
        for m in models:
            rs = [r for r in rollouts if r.task_id == tid and r.model == m]
            if rs:
                cells[(tid, m)] = summarize_cell(tid, m, rs)

    # Per-model leaderboard.
    model_metrics = {m: summarize_model(m, [r for r in rollouts if r.model == m]) for m in models}

    # Per-task buckets.
    task_buckets = {}
    for tid in task_ids:
        tcells = [cells[(tid, m)] for m in models if (tid, m) in cells]
        oracle_ok = bool(oracle.get(tid, {}).get("ok", True))
        task_buckets[tid] = classify_task(oracle_ok, tcells).value

    bucket_counts = {b.value: 0 for b in Bucket}
    for b in task_buckets.values():
        bucket_counts[b] += 1

    # "Why" analysis per task (drives the Deep Dive explanation panel).
    task_why = {}
    for tid in task_ids:
        tcells = [cells[(tid, m)] for m in models if (tid, m) in cells]
        task_why[tid] = _why(
            tcells, bool(oracle.get(tid, {}).get("ok", True)),
            task_buckets[tid], oracle.get(tid, {}),
        )

    report = {
        "run_dir": str(run_dir),
        "n_tasks": len(task_ids),
        "n_models": len(models),
        "n_rollouts": len(rollouts),
        "models": {m: _model_dict(mm) for m, mm in model_metrics.items()},
        "buckets": bucket_counts,
        "tasks": {
            tid: {
                "bucket": task_buckets[tid],
                "oracle_ok": bool(oracle.get(tid, {}).get("ok", True)),
                "cells": {
                    m: _cell_dict(cells[(tid, m)])
                    for m in models if (tid, m) in cells
                },
            }
            for tid in task_ids
        },
        "why": task_why,
    }
    return report


def _why(cells: list, oracle_ok: bool, bucket: str, oracle_rec: dict) -> dict:
    """Human explanation of a task's result — the 'why it's breaking' text."""
    if not oracle_ok:
        rg = oracle_rec.get("reward_golden")
        return {
            "headline": "Broken task — not a model failure.",
            "detail": (f"The golden (correct) solution itself scores {rg} instead of 1.0, "
                       "so the environment or reward.py is buggy. Model results here are "
                       "not meaningful until the task is fixed."),
            "tags": ["oracle-fail"],
        }

    # Aggregate outcomes + rewards across the task's cells.
    agg = {}
    rewards = []
    total = 0
    any_pass = False
    for c in cells:
        total += c.n_rollouts
        if c.n_success:
            any_pass = True
        for k, v in c.outcome_counts.items():
            agg[k] = agg.get(k, 0) + v
        rewards += [a["reward"] for a in c.attempts if a["reward"] is not None]
    best_mean = max((c.mean_reward for c in cells), default=0.0)
    fails = {k: v for k, v in agg.items() if k != "success"}
    dominant = max(fails, key=fails.get) if fails else "none"

    if bucket == "too_easy":
        return {"headline": "Too easy — low training signal.",
                "detail": "Every model solves this reliably across seeds.",
                "tags": ["saturated"]}
    if bucket == "productive":
        best = max(cells, key=lambda c: c.pass_rate)
        return {"headline": "Productive — solvable but discriminating.",
                "detail": (f"Best: {best.model} solved {best.n_success}/{best.n_rollouts}. "
                           "A real pass/fail spread across models = high RLVR signal."),
                "tags": ["good-signal"]}

    # model_breaking — explain HOW it breaks from the dominant failure mode.
    reason = {
        "truncated": ("Models run out of steps (hit max_steps) before finishing — "
                      "likely too long-horizon, or the correct UI path is hard to discover."),
        "zero": ("Models act but achieve nothing scored — they never find the right "
                 "approach (wrong target, wrong app affordance)."),
        "partial": (f"Models plateau at partial credit (best mean {best_mean:.2f}) but never "
                    "reach 1.0 — a specific sub-step blocks completion (e.g. a final "
                    "over-action penalty or a required field they miss)."),
        "error": ("Rollouts crash or reward.py returns no parseable score — an infra / "
                  "action-execution issue as much as a capability one."),
        "timeout": ("Rollouts exceed the wall-clock budget — the agent gets stuck / loops."),
    }.get(dominant, "No model made progress.")
    return {
        "headline": f"Model-breaking — 0 passes across {total} rollouts.",
        "detail": reason,
        "tags": ["model-breaking", f"dominant:{dominant}"],
    }


def _model_dict(mm) -> dict:
    return {
        "n_rollouts": mm.n_rollouts, "n_success": mm.n_success, "n_fail": mm.n_fail,
        "pass_rate": round(mm.pass_rate, 4), "mean_reward": round(mm.mean_reward, 4),
        "mean_steps": round(mm.mean_steps, 2),
        "outcome_counts": mm.outcome_counts, "fail_breakdown": mm.fail_breakdown,
        "by_domain": {k: round(v, 4) for k, v in mm.by_domain.items()},
    }


def _cell_dict(c) -> dict:
    return {
        "n_rollouts": c.n_rollouts, "n_success": c.n_success, "n_fail": c.n_fail,
        "solved": f"{c.n_success}/{c.n_rollouts}",
        "pass_rate": round(c.pass_rate, 4), "mean_reward": round(c.mean_reward, 4),
        "max_reward": round(c.max_reward, 4), "std_reward": round(c.std_reward, 4),
        "mean_steps": round(c.mean_steps, 2), "mean_duration_s": round(c.mean_duration_s, 1),
        "outcome_counts": c.outcome_counts, "attempts": c.attempts,
    }


# --- renderers --------------------------------------------------------------


def render_md(report: dict) -> str:
    L = []
    L.append(f"# CUA-Gym Benchmark Report\n")
    L.append(f"- tasks: **{report['n_tasks']}**  ·  models: **{report['n_models']}**  "
             f"·  rollouts: **{report['n_rollouts']}**\n")
    b = report["buckets"]
    L.append("## Task difficulty buckets\n")
    L.append(f"| Broken | Model-breaking | Too-easy | Productive |")
    L.append(f"|--:|--:|--:|--:|")
    L.append(f"| {b['broken']} | {b['model_breaking']} | {b['too_easy']} | {b['productive']} |\n")

    L.append("## Model leaderboard\n")
    L.append("| Model | Pass rate | Mean reward | Fails | zero | partial | truncated | error | timeout | Mean steps |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    for m, d in sorted(report["models"].items(), key=lambda kv: -kv[1]["pass_rate"]):
        oc = d["outcome_counts"]
        L.append(
            f"| {m} | {d['pass_rate']:.0%} | {d['mean_reward']:.2f} | {d['n_fail']} "
            f"| {oc['zero']} | {oc['partial']} | {oc['truncated']} | {oc['error']} "
            f"| {oc['timeout']} | {d['mean_steps']:.1f} |"
        )
    L.append("")
    L.append("## Per-task buckets\n")
    L.append("| Task | Bucket | Oracle | Best pass-rate |")
    L.append("|---|---|---|--:|")
    for tid, t in report["tasks"].items():
        best = max((c["pass_rate"] for c in t["cells"].values()), default=0.0)
        L.append(f"| {tid} | {t['bucket']} | {'ok' if t['oracle_ok'] else 'FAIL'} | {best:.0%} |")
    return "\n".join(L) + "\n"


def render_html(report: dict) -> str:
    b = report["buckets"]
    rows_models = ""
    for m, d in sorted(report["models"].items(), key=lambda kv: -kv[1]["pass_rate"]):
        oc = d["outcome_counts"]
        rows_models += (
            f"<tr><td>{m}</td><td>{d['pass_rate']:.0%}</td><td>{d['mean_reward']:.2f}</td>"
            f"<td>{d['n_fail']}</td><td>{oc['zero']}</td><td>{oc['partial']}</td>"
            f"<td>{oc['truncated']}</td><td>{oc['error']}</td><td>{oc['timeout']}</td>"
            f"<td>{d['mean_steps']:.1f}</td></tr>"
        )
    rows_tasks = ""
    palette = {"broken": "#f87171", "model_breaking": "#fbbf24",
               "too_easy": "#60a5fa", "productive": "#34d399"}
    for tid, t in report["tasks"].items():
        best = max((c["pass_rate"] for c in t["cells"].values()), default=0.0)
        color = palette.get(t["bucket"], "#888")
        rows_tasks += (
            f"<tr><td><code>{tid}</code></td>"
            f"<td><span class='pill' style='background:{color}22;color:{color}'>{t['bucket']}</span></td>"
            f"<td>{'ok' if t['oracle_ok'] else 'FAIL'}</td><td>{best:.0%}</td></tr>"
        )
    return f"""<title>CUA-Gym Benchmark Report</title>
<style>
body{{font:15px -apple-system,Segoe UI,Roboto,sans-serif;background:#0f1117;color:#e6e9ef;margin:0;padding:32px 20px}}
.wrap{{max-width:980px;margin:0 auto}} h1{{font-size:24px}} h2{{font-size:17px;border-bottom:1px solid #262b36;padding-bottom:6px;margin-top:28px}}
table{{border-collapse:collapse;width:100%;font-size:14px;min-width:560px}} th,td{{padding:8px 11px;border-bottom:1px solid #262b36;text-align:right}}
th:first-child,td:first-child{{text-align:left}} th{{color:#8b93a3}} .scroll{{overflow-x:auto}}
code{{background:#0b0d12;border:1px solid #262b36;border-radius:4px;padding:1px 6px}}
.pill{{padding:1px 9px;border-radius:20px;font-size:12px;font-weight:600}}
.cards{{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}} .card{{background:#181b23;border:1px solid #262b36;border-radius:10px;padding:14px 18px;flex:1;min-width:130px}}
.card .n{{font-size:24px;font-weight:700}} .card .l{{color:#8b93a3;font-size:13px}}
</style>
<div class="wrap">
<h1>CUA-Gym Benchmark Report</h1>
<div class="cards">
  <div class="card"><div class="n">{report['n_tasks']}</div><div class="l">tasks</div></div>
  <div class="card"><div class="n">{report['n_models']}</div><div class="l">models</div></div>
  <div class="card"><div class="n">{report['n_rollouts']}</div><div class="l">rollouts</div></div>
  <div class="card"><div class="n" style="color:#fbbf24">{b['model_breaking']}</div><div class="l">model-breaking</div></div>
  <div class="card"><div class="n" style="color:#f87171">{b['broken']}</div><div class="l">broken</div></div>
</div>
<h2>Model leaderboard <span style="color:#8b93a3;font-weight:400">(failures broken down by type)</span></h2>
<div class="scroll"><table>
<thead><tr><th>Model</th><th>Pass</th><th>Mean rwd</th><th>Fails</th><th>zero</th><th>partial</th><th>trunc</th><th>error</th><th>timeout</th><th>Steps</th></tr></thead>
<tbody>{rows_models}</tbody></table></div>
<h2>Per-task difficulty buckets</h2>
<div class="scroll"><table>
<thead><tr><th>Task</th><th>Bucket</th><th>Oracle</th><th>Best pass-rate</th></tr></thead>
<tbody>{rows_tasks}</tbody></table></div>
</div>
"""


_OUTCOME_STYLE = {
    "success":   ("✓", "#34d399"),
    "partial":   ("◐", "#a3e635"),
    "zero":      ("✗", "#f87171"),
    "truncated": ("⧗", "#fbbf24"),
    "error":     ("!", "#c084fc"),
    "timeout":   ("⏱", "#fb923c"),
}


def render_detail_html(report: dict) -> str:
    """Per-task × per-model grid: for each task, each model's K attempts —
    how many solved, each attempt's outcome/reward/time, and a verdict.
    """
    palette = {"broken": "#f87171", "model_breaking": "#fbbf24",
               "too_easy": "#60a5fa", "productive": "#34d399"}
    models = sorted(report["models"].keys())

    # Legend for the per-attempt glyphs.
    legend = " ".join(
        f"<span style='color:{c}'>{g}</span> {name}"
        for name, (g, c) in _OUTCOME_STYLE.items()
    )

    sections = ""
    # Order tasks: broken first, then model_breaking, then productive, then easy.
    order = {"broken": 0, "model_breaking": 1, "productive": 2, "too_easy": 3}
    for tid in sorted(report["tasks"], key=lambda t: order.get(report["tasks"][t]["bucket"], 9)):
        t = report["tasks"][tid]
        color = palette.get(t["bucket"], "#888")
        rows = ""
        for m in models:
            c = t["cells"].get(m)
            if not c:
                rows += f"<tr><td>{m}</td><td colspan='5' class='mut'>no rollouts</td></tr>"
                continue
            # per-attempt chips
            chips = ""
            for a in c["attempts"]:
                g, col = _OUTCOME_STYLE.get(a["outcome"], ("?", "#888"))
                rwd = "—" if a["reward"] is None else f"{a['reward']:.2f}"
                chips += (
                    f"<span class='chip' title='seed {a['seed']}: {a['outcome']}, "
                    f"reward={rwd}, {a['steps']} steps, {a['duration_s']}s' "
                    f"style='color:{col};border-color:{col}55'>{g} {rwd}</span>"
                )
            solved = c["solved"]
            solved_color = "#34d399" if c["n_success"] == c["n_rollouts"] else (
                "#f87171" if c["n_success"] == 0 else "#fbbf24")
            rows += (
                f"<tr><td>{m}</td>"
                f"<td style='color:{solved_color};font-weight:700'>{solved}</td>"
                f"<td>{c['mean_reward']:.2f}</td>"
                f"<td>{c['mean_duration_s']:.0f}s</td>"
                f"<td>{c['mean_steps']:.0f}</td>"
                f"<td class='chips'>{chips}</td></tr>"
            )
        oracle = "ok" if t["oracle_ok"] else "<b style='color:#f87171'>FAIL</b>"
        sections += f"""
<div class="task">
  <div class="thead">
    <code>{tid}</code>
    <span class="pill" style="background:{color}22;color:{color}">{t['bucket']}</span>
    <span class="mut">oracle: {oracle}</span>
  </div>
  <div class="scroll"><table>
    <thead><tr><th>Model</th><th>Solved</th><th>Mean rwd</th><th>Avg time</th><th>Steps</th><th>Per-attempt (seed 0…K−1)</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
</div>"""

    return f"""<title>CUA-Gym Benchmark — Per-Task Detail</title>
<style>
body{{font:15px -apple-system,Segoe UI,Roboto,sans-serif;background:#0f1117;color:#e6e9ef;margin:0;padding:28px 18px}}
.wrap{{max-width:1040px;margin:0 auto}} h1{{font-size:23px;margin:0 0 4px}}
.sub{{color:#8b93a3;margin:0 0 18px}} .legend{{font-size:13px;color:#8b93a3;margin:10px 0 22px}}
.task{{background:#161922;border:1px solid #262b36;border-radius:12px;padding:14px 16px;margin:14px 0}}
.thead{{display:flex;align-items:center;gap:12px;margin-bottom:10px}}
.thead code{{font-size:15px}} table{{border-collapse:collapse;width:100%;font-size:13.5px;min-width:640px}}
th,td{{padding:7px 10px;border-bottom:1px solid #222834;text-align:right;white-space:nowrap}}
th:first-child,td:first-child,td.chips{{text-align:left}} th{{color:#8b93a3;font-weight:600}}
.scroll{{overflow-x:auto}} .mut{{color:#8b93a3}}
code{{background:#0b0d12;border:1px solid #262b36;border-radius:4px;padding:1px 6px}}
.pill{{padding:1px 9px;border-radius:20px;font-size:12px;font-weight:700}}
.chip{{display:inline-block;border:1px solid;border-radius:6px;padding:1px 7px;margin:2px 3px 2px 0;font-size:12px;font-variant-numeric:tabular-nums}}
</style>
<div class="wrap">
<h1>Per-Task Detail — is each task model-breaking?</h1>
<p class="sub">Each task shows every model's K attempts: <b>Solved</b> = successes / total runs. Hover a chip for that attempt's seed, reward, steps, and time.</p>
<div class="legend">Legend: {legend} &nbsp;·&nbsp; chip shows outcome glyph + that run's reward</div>
{sections}
</div>
"""


# --- trajectories (for the Deep Dive view) ----------------------------------

_FAIL_PRIORITY = ["partial", "truncated", "zero", "timeout", "error"]


def build_trajectories(run_dir: Path, report: dict, max_steps_embed: int = 40) -> dict:
    """For each (task, model), pick ONE representative rollout and load its steps.

    Productive/too-easy -> show a success. Broken/model-breaking -> show the most
    informative failure. Screenshots are already data-URIs in the trace.
    """
    run_dir = Path(run_dir)
    traj: dict = {}
    for tid, t in report["tasks"].items():
        bucket = t["bucket"]
        traj[tid] = {}
        for model in t["cells"]:
            want_success = bucket in ("too_easy", "productive")
            chosen = _pick_seed(run_dir, tid, model, want_success)
            if chosen is None:
                continue
            trace = json.loads((run_dir / "rollouts" / f"{tid}__{model}__{chosen}.json").read_text())
            steps = []
            for s in trace.get("steps", [])[:max_steps_embed]:
                steps.append({
                    "index": s.get("index"),
                    "actions": s.get("actions", []),
                    "reasoning": s.get("reasoning", ""),
                    "screenshot": s.get("screenshot"),
                })
            res = trace.get("result", {})
            traj[tid][model] = {
                "seed": chosen, "outcome": res.get("outcome"),
                "reward": res.get("reward"), "duration_s": res.get("duration_s"),
                "n_steps": len(trace.get("steps", [])), "steps": steps,
            }
    return traj


def _pick_seed(run_dir: Path, tid: str, model: str, want_success: bool) -> int | None:
    cands = []
    for f in (run_dir / "rollouts").glob(f"{tid}__{model}__*.json"):
        seed = int(f.stem.rsplit("__", 1)[1])
        oc = json.loads(f.read_text()).get("result", {}).get("outcome", "zero")
        cands.append((seed, oc))
    if not cands:
        return None
    if want_success:
        succ = [s for s, oc in cands if oc == "success"]
        if succ:
            return min(succ)
    # else most-informative failure by priority, then any.
    for oc_want in _FAIL_PRIORITY:
        m = [s for s, oc in cands if oc == oc_want]
        if m:
            return min(m)
    return min(s for s, _ in cands)


def render_app_html(report: dict, trajectories: dict) -> str:
    """Single-page tabbed app: Overview + Deep Dive (task -> model -> trajectory)."""
    data = json.dumps({"report": report, "trajectories": trajectories})
    data = data.replace("</", "<\\/")  # safe inside <script>
    return _APP_TEMPLATE.replace("__DATA__", data)


def write_reports(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    report = analyze(run_dir)
    (run_dir / "report.json").write_text(json.dumps(report, indent=2))
    (run_dir / "report.md").write_text(render_md(report))
    (run_dir / "report.html").write_text(render_html(report))
    (run_dir / "report_detail.html").write_text(render_detail_html(report))
    trajectories = build_trajectories(run_dir, report)
    (run_dir / "index.html").write_text(render_app_html(report, trajectories))
    return report


_APP_TEMPLATE = r"""<title>CUA-Gym Benchmark</title>
<style>
:root{--bg:#0f1117;--card:#161922;--line:#262b36;--fg:#e6e9ef;--mut:#8b93a3;--accent:#60a5fa}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--fg);font:14.5px -apple-system,Segoe UI,Roboto,sans-serif}
header{padding:16px 22px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:16px;position:sticky;top:0;background:var(--bg);z-index:5}
h1{font-size:18px;margin:0} .tabs{display:flex;gap:6px;margin-left:auto}
.tab{padding:7px 15px;border:1px solid var(--line);border-radius:8px;cursor:pointer;color:var(--mut)}
.tab.on{color:var(--fg);background:var(--card);border-color:#3a4763}
.wrap{max-width:1120px;margin:0 auto;padding:20px}
.cards{display:flex;gap:12px;flex-wrap:wrap;margin:6px 0 20px}
.c{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;flex:1;min-width:120px}
.c .n{font-size:23px;font-weight:700} .c .l{color:var(--mut);font-size:12.5px}
table{border-collapse:collapse;width:100%;font-size:13.5px;min-width:560px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left} th{color:var(--mut)}
.scroll{overflow-x:auto} code{background:#0b0d12;border:1px solid var(--line);border-radius:4px;padding:1px 6px}
.pill{padding:1px 9px;border-radius:20px;font-size:12px;font-weight:700}
h2{font-size:16px;border-bottom:1px solid var(--line);padding-bottom:6px;margin:26px 0 12px}
.dd{display:flex;gap:18px} .side{width:250px;flex:none} .main{flex:1;min-width:0}
.grp{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.06em;margin:12px 0 5px}
.titem{padding:7px 10px;border:1px solid var(--line);border-radius:8px;margin:4px 0;cursor:pointer;display:flex;justify-content:space-between;gap:8px}
.titem:hover{border-color:#3a4763} .titem.on{background:var(--card);border-color:var(--accent)}
.titem code{background:none;border:none;padding:0} .dot{width:8px;height:8px;border-radius:50%;flex:none;margin-top:5px}
.why{background:var(--card);border-left:3px solid var(--accent);border-radius:8px;padding:12px 15px;margin:10px 0 16px}
.why b{font-size:15px} .why p{margin:6px 0 0;color:#cdd3df}
.chips{display:flex;gap:7px;flex-wrap:wrap;margin:10px 0}
.mchip{border:1px solid var(--line);border-radius:8px;padding:6px 11px;cursor:pointer}
.mchip.on{border-color:var(--accent);background:#182234} .mchip small{color:var(--mut)}
.stat{color:var(--mut);margin:8px 0 4px} .stat b{color:var(--fg)}
.step{display:flex;gap:14px;padding:12px 0;border-bottom:1px solid var(--line)}
.shot{width:280px;flex:none;border:1px solid var(--line);border-radius:8px;background:#0b0d12;aspect-ratio:16/10;object-fit:contain}
.noshot{width:280px;flex:none;border:1px dashed var(--line);border-radius:8px;height:175px;display:flex;align-items:center;justify-content:center;color:var(--mut);font-size:12px}
.si{font-weight:700;color:var(--accent)} .act{margin:4px 0;font-family:ui-monospace,monospace;font-size:12.5px;color:#d7deea}
.rez{color:var(--mut);font-size:13px;white-space:pre-wrap} .mut{color:var(--mut)}
</style>
<header>
  <h1>🧪 CUA-Gym Benchmark</h1>
  <div class="tabs">
    <div class="tab on" data-tab="overview" onclick="showTab('overview')">Overview</div>
    <div class="tab" data-tab="deep" onclick="showTab('deep')">Deep Dive</div>
  </div>
</header>
<div class="wrap">
  <div id="overview"></div>
  <div id="deep" style="display:none"></div>
</div>
<script>
const DATA = __DATA__;
const R = DATA.report, TRAJ = DATA.trajectories;
const BUCKET = {broken:"#f87171",model_breaking:"#fbbf24",too_easy:"#60a5fa",productive:"#34d399"};
const OC = {success:["✓","#34d399"],partial:["◐","#a3e635"],zero:["✗","#f87171"],
            truncated:["⧗","#fbbf24"],error:["!","#c084fc"],timeout:["⏱","#fb923c"]};
const esc = s => (s||"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const pct = x => Math.round((x||0)*100)+"%";

function showTab(t){
  document.querySelectorAll(".tab").forEach(e=>e.classList.toggle("on",e.dataset.tab===t));
  overview.style.display = t==="overview"?"block":"none";
  deep.style.display = t==="deep"?"block":"none";
}

function renderOverview(){
  const b=R.buckets;
  let h=`<div class="cards">
    <div class="c"><div class="n">${R.n_tasks}</div><div class="l">tasks</div></div>
    <div class="c"><div class="n">${R.n_models}</div><div class="l">models</div></div>
    <div class="c"><div class="n">${R.n_rollouts}</div><div class="l">rollouts</div></div>
    <div class="c"><div class="n" style="color:#fbbf24">${b.model_breaking}</div><div class="l">model-breaking</div></div>
    <div class="c"><div class="n" style="color:#f87171">${b.broken}</div><div class="l">broken</div></div>
    <div class="c"><div class="n" style="color:#34d399">${b.productive}</div><div class="l">productive</div></div>
  </div>`;
  h+=`<h2>Model leaderboard</h2><div class="scroll"><table><thead><tr>
    <th>Model</th><th>Pass</th><th>Mean rwd</th><th>Fails</th><th>zero</th><th>partial</th>
    <th>trunc</th><th>error</th><th>timeout</th><th>Steps</th></tr></thead><tbody>`;
  Object.entries(R.models).sort((a,b)=>b[1].pass_rate-a[1].pass_rate).forEach(([m,d])=>{
    const o=d.outcome_counts;
    h+=`<tr><td>${m}</td><td>${pct(d.pass_rate)}</td><td>${d.mean_reward.toFixed(2)}</td>
      <td>${d.n_fail}</td><td>${o.zero}</td><td>${o.partial}</td><td>${o.truncated}</td>
      <td>${o.error}</td><td>${o.timeout}</td><td>${d.mean_steps.toFixed(1)}</td></tr>`;
  });
  h+=`</tbody></table></div><h2>Tasks</h2><div class="scroll"><table><thead><tr>
    <th>Task</th><th>Bucket</th><th>Oracle</th><th>Best pass</th><th>Why</th></tr></thead><tbody>`;
  Object.entries(R.tasks).forEach(([tid,t])=>{
    const best=Math.max(0,...Object.values(t.cells).map(c=>c.pass_rate));
    const col=BUCKET[t.bucket]||"#888";
    h+=`<tr><td><code>${tid}</code></td>
      <td><span class="pill" style="background:${col}22;color:${col}">${t.bucket}</span></td>
      <td>${t.oracle_ok?"ok":"<b style='color:#f87171'>FAIL</b>"}</td>
      <td>${pct(best)}</td><td style="text-align:left;white-space:normal;color:var(--mut)">${esc(R.why[tid].headline)}</td></tr>`;
  });
  h+=`</tbody></table></div>`;
  overview.innerHTML=h;
}

let curTask=null, curModel=null;
function renderDeep(){
  const order={broken:0,model_breaking:1,productive:2,too_easy:3};
  const tids=Object.keys(R.tasks).sort((a,b)=>(order[R.tasks[a].bucket]??9)-(order[R.tasks[b].bucket]??9));
  let side=`<div class="side">`;
  let lastB=null;
  tids.forEach(tid=>{
    const t=R.tasks[tid], col=BUCKET[t.bucket]||"#888";
    if(t.bucket!==lastB){ side+=`<div class="grp">${t.bucket.replace("_"," ")}</div>`; lastB=t.bucket; }
    const best=Math.max(0,...Object.values(t.cells).map(c=>c.pass_rate));
    side+=`<div class="titem ${tid===curTask?'on':''}" onclick="selTask('${tid}')">
      <span class="dot" style="background:${col}"></span>
      <code style="flex:1">${tid}</code><small class="mut">${pct(best)}</small></div>`;
  });
  side+=`</div>`;
  deep.innerHTML=`<div class="dd">${side}<div class="main" id="main"></div></div>`;
  if(!curTask) curTask=tids[0];
  selTask(curTask);
}

function selTask(tid){
  curTask=tid;
  document.querySelectorAll(".titem").forEach(e=>e.classList.toggle("on",
    e.querySelector("code").textContent===tid));
  const t=R.tasks[tid], w=R.why[tid], col=BUCKET[t.bucket]||"#888";
  const models=Object.keys(t.cells);
  curModel = (curModel && t.cells[curModel])?curModel:models[0];
  let h=`<h2 style="margin-top:0"><code>${tid}</code>
    <span class="pill" style="background:${col}22;color:${col};margin-left:8px">${t.bucket}</span>
    <span class="mut" style="font-size:13px;margin-left:8px">oracle: ${t.oracle_ok?"ok":"<b style='color:#f87171'>FAIL</b>"}</span></h2>`;
  h+=`<div class="why"><b>${esc(w.headline)}</b><p>${esc(w.detail)}</p></div>`;
  h+=`<div class="chips">`;
  models.forEach(m=>{
    const c=t.cells[m], sc=c.n_success===c.n_rollouts?"#34d399":(c.n_success===0?"#f87171":"#fbbf24");
    h+=`<div class="mchip ${m===curModel?'on':''}" onclick="selModel('${m}')">${m}
      <small> — <b style="color:${sc}">${c.solved}</b></small></div>`;
  });
  h+=`</div><div id="traj"></div>`;
  document.getElementById("main").innerHTML=h;
  selModel(curModel);
}

function selModel(m){
  curModel=m;
  document.querySelectorAll(".mchip").forEach(e=>e.classList.toggle("on",
    e.textContent.trim().startsWith(m)));
  const t=R.tasks[curTask], c=t.cells[m];
  const tr=(TRAJ[curTask]||{})[m];
  let h="";
  const oc=c.outcome_counts;
  h+=`<div class="stat">Solved <b>${c.solved}</b> · mean reward <b>${c.mean_reward.toFixed(2)}</b>
     · avg time <b>${c.mean_duration_s}s</b> · mean steps <b>${c.mean_steps.toFixed(0)}</b>
     · outcomes ${Object.entries(oc).filter(([,v])=>v).map(([k,v])=>{
        const g=OC[k]||["?","#888"];return `<span style="color:${g[1]}">${g[0]}${v}</span>`}).join(" ")}</div>`;
  if(!tr){ h+=`<p class="mut">No trajectory recorded for this cell.</p>`; document.getElementById("traj").innerHTML=h; return; }
  const g=OC[tr.outcome]||["?","#888"];
  h+=`<div class="stat">Shown trajectory — seed ${tr.seed}, outcome
     <b style="color:${g[1]}">${g[0]} ${tr.outcome}</b>, reward <b>${tr.reward}</b>,
     ${tr.n_steps} steps, ${tr.duration_s}s</div>`;
  tr.steps.forEach(s=>{
    const shot = s.screenshot
      ? `<img class="shot" src="${s.screenshot}" loading="lazy">`
      : `<div class="noshot">no screenshot</div>`;
    h+=`<div class="step">${shot}<div>
        <div class="si">step ${s.index}</div>
        ${(s.actions||[]).map(a=>`<div class="act">▸ ${esc(a)}</div>`).join("")}
        ${s.reasoning?`<div class="rez">${esc(s.reasoning)}</div>`:""}
      </div></div>`;
  });
  document.getElementById("traj").innerHTML=h;
}

renderOverview(); renderDeep();
</script>
"""


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    args = ap.parse_args()
    report = write_reports(Path(args.run_dir))
    print(json.dumps(report["buckets"], indent=2))
    print(f"Wrote report.json / report.md / report.html under {args.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
