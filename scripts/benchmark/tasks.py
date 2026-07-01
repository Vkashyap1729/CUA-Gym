"""Load verified CUA-Gym tasks from output/final/<id>/.

A benchmarkable task is a final task dir with the 4 pipeline artifacts
(config.json + initial_setup.py + golden_patch.py + reward.py). REVIEW.md is
optional. config.json field names follow the pipeline contract:
`id` / `instruction` / `app_type` / `config` / `evaluator`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# app_type values that are pure-HTTP mock websites (can run locally with no VM).
# Everything else (libreoffice_calc, gimp, vs_code, ...) is a desktop task and
# requires the OSWorld VM for both setup and GUI rollout.
WEB_APP_TYPE = "mock_websites"

REQUIRED_FILES = ("config.json", "initial_setup.py", "golden_patch.py", "reward.py")


@dataclass
class Task:
    task_id: str
    instruction: str
    app_type: str
    task_dir: Path
    config: dict  # full parsed config.json

    @property
    def is_web(self) -> bool:
        return self.app_type == WEB_APP_TYPE

    @property
    def initial_setup(self) -> Path:
        return self.task_dir / "initial_setup.py"

    @property
    def golden_patch(self) -> Path:
        return self.task_dir / "golden_patch.py"

    @property
    def reward(self) -> Path:
        return self.task_dir / "reward.py"

    def __repr__(self) -> str:
        return f"Task({self.task_id!r}, app_type={self.app_type!r})"


def is_complete(task_dir: Path) -> bool:
    """True iff all 4 pipeline artifacts exist and config.json is valid JSON."""
    task_dir = Path(task_dir)
    if not all((task_dir / f).exists() for f in REQUIRED_FILES):
        return False
    try:
        json.loads((task_dir / "config.json").read_text())
    except (json.JSONDecodeError, OSError):
        return False
    return True


def load_task(task_dir: str | Path) -> Task:
    """Load a single final task dir into a Task. Raises ValueError if incomplete."""
    task_dir = Path(task_dir)
    if not is_complete(task_dir):
        raise ValueError(f"{task_dir} is not a complete final task (missing one of {REQUIRED_FILES})")
    cfg = json.loads((task_dir / "config.json").read_text())
    return Task(
        task_id=cfg.get("id", task_dir.name),
        instruction=cfg["instruction"],
        app_type=cfg.get("app_type", "unknown"),
        task_dir=task_dir,
        config=cfg,
    )


def load_tasks(final_dir: str | Path = "output/final") -> list[Task]:
    """Load every complete task under output/final/, sorted by task_id."""
    final_dir = Path(final_dir)
    if not final_dir.exists():
        return []
    tasks = []
    for child in sorted(final_dir.iterdir()):
        if child.is_dir() and is_complete(child):
            tasks.append(load_task(child))
    return tasks
