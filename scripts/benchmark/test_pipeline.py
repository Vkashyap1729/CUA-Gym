"""End-to-end pipeline test with NO VM and NO model calls.

Validates: model-adapter action parsing, the rollout engine (loop + outcome
classification), the async resumable runner (concurrency + resume), and the
analysis/report stage — by wiring FakeBackend + ScriptedAgent and synthetic
rewards. Produces a real report.{json,md,html} under a temp run dir.

Run:  python scripts/benchmark/test_pipeline.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.benchmark import actions as A  # noqa: E402
from scripts.benchmark.agents.anthropic_cua import parse_tool_input  # noqa: E402
from scripts.benchmark.agents.base import ScriptedAgent  # noqa: E402
from scripts.benchmark.agents.openai_cua import parse_computer_call  # noqa: E402
from scripts.benchmark.analysis import write_reports  # noqa: E402
from scripts.benchmark.env_backend import FakeBackend  # noqa: E402
from scripts.benchmark.metrics import Outcome, classify_outcome, classify_task, summarize_cell  # noqa: E402
from scripts.benchmark.rollout import run_episode  # noqa: E402
from scripts.benchmark.runner import run_benchmark  # noqa: E402
from scripts.benchmark.tasks import load_tasks  # noqa: E402

_fail = []


def check(name, cond, detail=""):
    print(f"  [{'ok' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail and not cond else ""))
    if not cond:
        _fail.append(name)


def _task(tid="t", app="mock_websites"):
    return SimpleNamespace(task_id=tid, app_type=app, instruction="do the thing",
                           is_web=True, initial_setup=None, golden_patch=None, reward=None)


def test_adapter_parsing():
    print("adapter action parsing:")
    # Anthropic
    check("anthropic_click", parse_tool_input("computer", {"action": "left_click", "coordinate": [5, 6]}) == A.Click(5, 6))
    check("anthropic_double", parse_tool_input("computer", {"action": "double_click", "coordinate": [1, 2]}).clicks == 2)
    check("anthropic_type", parse_tool_input("computer", {"action": "type", "text": "hi"}) == A.TypeText("hi"))
    chord = parse_tool_input("computer", {"action": "key", "text": "ctrl+c"})
    check("anthropic_key_chord", isinstance(chord, A.KeyPress) and chord.keys == ["ctrl", "c"])
    sc = parse_tool_input("computer", {"action": "scroll", "coordinate": [0, 0], "scroll_direction": "down", "scroll_amount": 4})
    check("anthropic_scroll", isinstance(sc, A.Scroll) and sc.dy == 4)
    check("anthropic_screenshot", isinstance(parse_tool_input("computer", {"action": "screenshot"}), A.Screenshot))
    # OpenAI
    check("openai_click", parse_computer_call({"type": "click", "x": 3, "y": 4, "button": "left"}) == A.Click(3, 4))
    kp = parse_computer_call({"type": "keypress", "keys": ["ENTER"]})
    check("openai_keypress", isinstance(kp, A.KeyPress) and kp.keys == ["enter"])
    dr = parse_computer_call({"type": "drag", "path": [{"x": 0, "y": 0}, {"x": 9, "y": 9}]})
    check("openai_drag", isinstance(dr, A.Drag) and (dr.x2, dr.y2) == (9, 9))
    check("openai_type", parse_computer_call({"type": "type", "text": "yo"}) == A.TypeText("yo"))


def test_outcome_classification():
    print("outcome classification:")
    check("success", classify_outcome(1.0, terminated=True, truncated=False, errored=False, timed_out=False) is Outcome.SUCCESS)
    check("partial", classify_outcome(0.6, terminated=True, truncated=False, errored=False, timed_out=False) is Outcome.PARTIAL)
    check("zero", classify_outcome(0.0, terminated=True, truncated=False, errored=False, timed_out=False) is Outcome.ZERO)
    check("truncated", classify_outcome(0.0, terminated=False, truncated=True, errored=False, timed_out=False) is Outcome.TRUNCATED)
    check("error", classify_outcome(None, terminated=False, truncated=False, errored=True, timed_out=False) is Outcome.ERROR)
    check("timeout", classify_outcome(None, terminated=False, truncated=False, errored=False, timed_out=True) is Outcome.TIMEOUT)
    check("no_reward_is_error", classify_outcome(None, terminated=True, truncated=False, errored=False, timed_out=False) is Outcome.ERROR)


def test_rollout_engine():
    print("rollout engine:")
    task = _task()
    script = [[A.Click(10, 20)], [A.TypeText("hello")], [A.Done()]]
    # Passing rollout
    be = FakeBackend(reward_for=1.0)
    res, trace = run_episode(task, ScriptedAgent(script, name="m"), be, seed=0, max_steps=25)
    check("pass_outcome", res.outcome is Outcome.SUCCESS, res.outcome)
    check("actions_executed", len(be.executed) == 2, be.executed)  # Click + Type (Done is not executed)
    check("teardown_called", be.teardown_count == 1)
    check("trace_steps", len(trace["steps"]) == 3)
    # Failing (zero) rollout
    res0, _ = run_episode(task, ScriptedAgent(script, name="m"), FakeBackend(reward_for=0.0), seed=1)
    check("zero_outcome", res0.outcome is Outcome.ZERO, res0.outcome)
    # Truncation: agent never says Done
    never_done = [[A.Click(1, 1)]] * 50
    rest, _ = run_episode(task, ScriptedAgent(never_done, name="m"), FakeBackend(reward_for=0.0), seed=2, max_steps=3)
    check("truncated_outcome", rest.outcome is Outcome.TRUNCATED, rest.outcome)
    check("truncated_steps", rest.steps == 3)
    # Error: backend.score raises
    def boom(_):
        raise RuntimeError("vm gone")
    bad = FakeBackend(reward_for=boom)
    rese, _ = run_episode(task, ScriptedAgent(script, name="m"), bad, seed=3)
    check("error_outcome", rese.outcome is Outcome.ERROR, rese.outcome)
    check("error_teardown_still_called", bad.teardown_count == 1)


def _make_synthetic_final(final_dir: Path, task_ids: list[str]) -> None:
    """Create minimal-but-complete task dirs (FakeBackend never runs the scripts)."""
    for tid in task_ids:
        d = final_dir / tid
        d.mkdir(parents=True)
        (d / "config.json").write_text(json.dumps({
            "id": tid, "instruction": f"do {tid}", "app_type": "mock_websites",
            "config": [{"type": "execute", "command": ["python3", "initial_setup.py"]}],
            "evaluator": {"type": "python", "url": "reward.py"},
        }))
        for fn in ("initial_setup.py", "golden_patch.py", "reward.py"):
            (d / fn).write_text("# stub\n")


def test_runner_and_analysis():
    print("runner + analysis (full pipeline):")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        final_dir = tmp / "final"
        task_ids = ["task_a", "task_b", "task_c"]
        _make_synthetic_final(final_dir, task_ids)
        check("synthetic_tasks_complete", len(load_tasks(final_dir)) == 3)

        # strong model passes everything; weak passes only task_b -> mixed buckets.
        rewards = {}
        for i, tid in enumerate(task_ids):
            rewards[("strong", tid)] = 1.0
            rewards[("weak", tid)] = 1.0 if tid == "task_b" else 0.0

        holder = {"m": None}

        def agent_factory2(model_key):
            holder["m"] = model_key
            return ScriptedAgent([[A.Click(5, 5)], [A.Done()]], name=model_key)

        def make_backend(task):
            return FakeBackend(reward_for=rewards[(holder["m"], task.task_id)])

        def backend_factory_for(_):
            return make_backend

        run_dir = tmp / "run1"
        summary = run_benchmark(
            run_dir=run_dir, task_ids=task_ids, final_dir=str(final_dir),
            models=["strong", "weak"], seeds=2, max_steps=5, concurrency=1,
            backend_factory=backend_factory_for(holder), agent_factory=agent_factory2,
            oracle_fn=lambda t: {"ok": True},
        )
        check("ran_all", summary["ran"] == 3 * 2 * 2, summary)

        # Resume: second run should skip everything.
        summary2 = run_benchmark(
            run_dir=run_dir, task_ids=task_ids, final_dir=str(final_dir),
            models=["strong", "weak"], seeds=2, max_steps=5, concurrency=1,
            backend_factory=backend_factory_for(holder), agent_factory=agent_factory2,
            oracle_fn=lambda t: {"ok": True},
        )
        check("resume_skips_all", summary2["skipped"] == 3 * 2 * 2 and summary2["ran"] == 0, summary2)

        report = write_reports(run_dir)
        check("report_rollouts", report["n_rollouts"] == 12, report["n_rollouts"])
        check("report_models", report["n_models"] == 2)
        check("strong_pass_100", report["models"]["strong"]["pass_rate"] == 1.0)
        check("weak_fails_counted", report["models"]["weak"]["n_fail"] > 0)
        # task[0]: strong passes, weak fails -> productive
        check("task0_productive", report["tasks"][task_ids[0]]["bucket"] == "productive",
              report["tasks"][task_ids[0]]["bucket"])
        # task[1]: both pass -> too_easy
        check("task1_too_easy", report["tasks"][task_ids[1]]["bucket"] == "too_easy",
              report["tasks"][task_ids[1]]["bucket"])
        for f in ("report.json", "report.md", "report.html"):
            check(f"wrote_{f}", (run_dir / f).exists())
        # broken bucket via failing oracle
        bk = classify_task(False, [])
        check("broken_via_oracle", bk.value == "broken")


def main():
    test_adapter_parsing()
    test_outcome_classification()
    test_rollout_engine()
    test_runner_and_analysis()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} -> {_fail}")
        return 1
    print("All pipeline tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
