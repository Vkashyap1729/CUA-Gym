"""Oracle control: prove a task is solvable before blaming the models.

For each task we run the dual-env reward anchors:
  initial_setup.py            -> reward.py   expect 0.0
  initial_setup + golden_patch -> reward.py   expect 1.0

If this fails the task itself is BROKEN (env/reward bug) and any model failure is
meaningless. If it passes, a 0% model pass-rate is a real MODEL-BREAKING signal.

Web (mock_websites) tasks run locally with no VM by reusing
scripts/local/local_verify.verify_task. Desktop tasks need the VM and are routed
through the VM oracle (Phase 3 — not yet wired; raises NotImplementedError).
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from .tasks import Task

_REPO = Path(__file__).resolve().parents[2]
_LOCAL_VERIFY = _REPO / "scripts" / "local" / "local_verify.py"

# cua-gym-<name>.xlang.ai  ->  hub mock app name (hyphens become underscores).
_XLANG_HOST_RE = re.compile(r"cua-gym-([a-z0-9_-]+)\.xlang\.ai")

# Default local ports per mock app (matches scripts/local/config.json convention).
DEFAULT_PORTS = {
    "gmail": 5173,
    "google_calendar": 5174,
    "google_docs": 5175,
}


def _load_local_verify():
    spec = importlib.util.spec_from_file_location("cua_local_verify", _LOCAL_VERIFY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def detect_mock_app(task: Task) -> str | None:
    """Infer the mock app name from the xlang.ai host referenced in the scripts."""
    apps: set[str] = set()
    for fname in ("reward.py", "initial_setup.py", "golden_patch.py"):
        text = (task.task_dir / fname).read_text()
        for m in _XLANG_HOST_RE.findall(text):
            apps.add(m.replace("-", "_"))
    if len(apps) == 1:
        return apps.pop()
    if len(apps) > 1:
        # Multi-mock task: local_verify localizes to a single URL, so flag it.
        return None
    return None


def oracle_check_web(task: Task, mock_url: str, python: str | None = None) -> dict:
    """Run the dual-env oracle for a web task. Returns a normalized result dict."""
    lv = _load_local_verify()
    kwargs = {"mock_url": mock_url}
    if python:
        kwargs["python"] = python
    res = lv.verify_task(str(task.task_dir), verbose=False, **kwargs)
    return {
        "task_id": task.task_id,
        "ok": bool(res.get("pass")),
        "reward_initial": res.get("reward_initial"),
        "reward_golden": res.get("reward_golden"),
        "forbidden_warnings": res.get("forbidden_warnings", []),
        "error": res.get("error"),
    }


def oracle_check(task: Task, mock_url: str | None = None, python: str | None = None) -> dict:
    """Run the oracle control for a task, dispatching by app_type."""
    if task.is_web:
        if not mock_url:
            raise ValueError(f"web task {task.task_id} requires a mock_url")
        return oracle_check_web(task, mock_url, python)
    raise NotImplementedError(
        f"desktop oracle (app_type={task.app_type!r}) needs the VM — wired in Phase 3"
    )
