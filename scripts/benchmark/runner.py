"""Async, concurrency-limited, resumable benchmark driver.

Unit of work = one (task, model, seed) rollout. Before any rollout, runs the
ORACLE control once per task (caches it) so broken tasks are flagged up front.
Mirrors batch_orchestrator.py: asyncio.Semaphore for bounded parallelism, atomic
status.json writes, skip-if-already-done resume.

Rollouts are blocking (HTTP to VM + model API), so they run in a thread pool via
run_in_executor; the semaphore bounds concurrent VMs.

Testable: backend_factory(task) and agent_factory(model_key) are injected, so the
whole driver runs against FakeBackend + ScriptedAgent with no VM/model.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from .agents.registry import build_agent, panel_keys
from .metrics import Outcome
from .rollout import run_episode
from .tasks import Task, load_task


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(path)


class BenchmarkRunner:
    def __init__(
        self,
        run_dir: Path,
        models: list[str],
        seeds: int = 5,
        max_steps: int = 25,
        concurrency: int = 8,
        backend_factory=None,
        agent_factory=build_agent,
        oracle_fn=None,
        now=time.time,
    ):
        self.run_dir = Path(run_dir)
        self.models = models
        self.seeds = seeds
        self.max_steps = max_steps
        self.concurrency = concurrency
        self.backend_factory = backend_factory
        self.agent_factory = agent_factory
        self.oracle_fn = oracle_fn  # callable(task) -> {"ok": bool, ...}; may be None
        self.now = now

        self.status_file = self.run_dir / "status.json"
        self.rollouts_dir = self.run_dir / "rollouts"
        self.oracle_dir = self.run_dir / "oracle"
        self.status = self._load_status()

    def _load_status(self) -> dict:
        if self.status_file.exists():
            return json.loads(self.status_file.read_text())
        return {"rollouts": {}, "oracle": {}}

    def _save_status(self) -> None:
        _atomic_write(self.status_file, self.status)

    @staticmethod
    def unit_key(task_id: str, model: str, seed: int) -> str:
        return f"{task_id}__{model}__{seed}"

    def _rollout_path(self, key: str) -> Path:
        return self.rollouts_dir / f"{key}.json"

    def _is_done(self, key: str) -> bool:
        rec = self.status["rollouts"].get(key)
        if rec and rec.get("outcome") and self._rollout_path(key).exists():
            return True
        return False

    # --- oracle ---

    def _run_oracle(self, task: Task) -> dict:
        cached = self.status["oracle"].get(task.task_id)
        if cached is not None:
            return cached
        if self.oracle_fn is None:
            res = {"ok": True, "skipped": True}
        else:
            res = self.oracle_fn(task)
        self.status["oracle"][task.task_id] = res
        _atomic_write(self.oracle_dir / f"{task.task_id}.json", res)
        self._save_status()
        return res

    # --- one rollout (blocking; called in executor) ---

    def _do_rollout(self, task: Task, model: str, seed: int) -> dict:
        agent = self.agent_factory(model)
        backend = self.backend_factory(task)
        result, trace = run_episode(
            task, agent, backend, seed=seed, max_steps=self.max_steps,
        )
        key = self.unit_key(task.task_id, model, seed)
        _atomic_write(self._rollout_path(key), trace)
        return result.to_dict()

    async def _worker(self, task: Task, model: str, seed: int, sem: asyncio.Semaphore):
        key = self.unit_key(task.task_id, model, seed)
        if self._is_done(key):
            return ("skip", key)
        async with sem:
            loop = asyncio.get_event_loop()
            try:
                rec = await loop.run_in_executor(None, self._do_rollout, task, model, seed)
            except Exception as exc:  # noqa: BLE001
                rec = {"outcome": Outcome.ERROR.value, "error": f"{type(exc).__name__}: {exc}",
                       "reward": None, "task_id": task.task_id, "model": model, "seed": seed}
            self.status["rollouts"][key] = {
                "outcome": rec.get("outcome"), "reward": rec.get("reward"),
                "finished_at": self.now(),
            }
            self._save_status()
            return ("done", key)

    async def run(self, tasks: list[Task]) -> dict:
        # 1. Oracle gate (sequential — cheap, and informs nothing downstream blocks on it).
        for t in tasks:
            self._run_oracle(t)

        # 2. Fan out rollouts.
        sem = asyncio.Semaphore(self.concurrency)
        jobs = [
            self._worker(t, m, s, sem)
            for t in tasks for m in self.models for s in range(self.seeds)
        ]
        results = await asyncio.gather(*jobs)
        done = sum(1 for kind, _ in results if kind == "done")
        skipped = sum(1 for kind, _ in results if kind == "skip")
        return {"total": len(jobs), "ran": done, "skipped": skipped}


def run_benchmark(
    run_dir,
    task_ids: list[str],
    final_dir: str = "output/final",
    models: list[str] | None = None,
    seeds: int = 5,
    max_steps: int = 25,
    concurrency: int = 8,
    backend_factory=None,
    agent_factory=build_agent,
    oracle_fn=None,
) -> dict:
    """Synchronous entrypoint. Loads tasks by id and runs the async driver."""
    tasks = [load_task(Path(final_dir) / tid) for tid in task_ids]
    runner = BenchmarkRunner(
        run_dir=Path(run_dir),
        models=models or panel_keys(),
        seeds=seeds,
        max_steps=max_steps,
        concurrency=concurrency,
        backend_factory=backend_factory,
        agent_factory=agent_factory,
        oracle_fn=oracle_fn,
    )
    return asyncio.run(runner.run(tasks))
