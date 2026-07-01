"""Metrics + failure taxonomy for the benchmark.

This module defines EXACTLY what you get out of a benchmark run. Three levels:

  1. Per-rollout outcome     — one episode of (task, model, seed)
  2. Per-(task, model) cell   — aggregate over the K seeds
  3. Per-model / per-task / per-domain rollups + task difficulty buckets

A rollout ends in exactly one Outcome:

  SUCCESS    reward == 1.0
  PARTIAL    0.0 < reward < 1.0          (made scored progress, didn't finish)
  ZERO       reward == 0.0               (ran cleanly, accomplished nothing scored)
  TRUNCATED  hit max_steps without Done  (ran out of budget)
  ERROR      exception in env/model/action
  TIMEOUT    exceeded wall-clock budget

"Failure" = anything that is not SUCCESS. n_fail = n_rollouts - n_success, and it
is further broken down by the outcomes above so you can tell *how* it failed
(stuck at zero vs. partial vs. crashed vs. timed out).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from statistics import mean, pstdev


class Outcome(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    ZERO = "zero"
    TRUNCATED = "truncated"
    ERROR = "error"
    TIMEOUT = "timeout"

    @property
    def is_fail(self) -> bool:
        return self is not Outcome.SUCCESS


def classify_outcome(reward: float | None, *, terminated: bool, truncated: bool,
                     errored: bool, timed_out: bool) -> Outcome:
    if errored:
        return Outcome.ERROR
    if timed_out:
        return Outcome.TIMEOUT
    if reward is None:
        return Outcome.ERROR  # reward.py produced no parseable score
    if reward >= 1.0:
        return Outcome.SUCCESS
    if truncated and not terminated:
        return Outcome.TRUNCATED
    if reward > 0.0:
        return Outcome.PARTIAL
    return Outcome.ZERO


# Task difficulty buckets (the "model-breaking" check).
class Bucket(str, Enum):
    BROKEN = "broken"               # oracle != 1.0 — task/reward bug
    MODEL_BREAKING = "model_breaking"  # oracle ok, no model makes progress
    TOO_EASY = "too_easy"           # every model solves it reliably
    PRODUCTIVE = "productive"       # mixed — high RLVR signal


@dataclass
class RolloutResult:
    """One episode. This is what gets written to rollouts/<task>__<model>__<seed>.json."""

    task_id: str
    model: str
    seed: int
    reward: float | None
    outcome: Outcome
    steps: int                 # number of agent turns taken
    n_actions: int             # total primitive actions executed
    duration_s: float
    error: str | None = None
    app_type: str = "unknown"

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["outcome"] = self.outcome.value
        return d


@dataclass
class CellMetrics:
    """Aggregate over the K seeds of one (task, model)."""

    task_id: str
    model: str
    n_rollouts: int
    n_success: int
    n_fail: int
    pass_rate: float
    mean_reward: float
    max_reward: float
    std_reward: float
    mean_steps: float
    mean_duration_s: float
    outcome_counts: dict  # Outcome.value -> count
    attempts: list = field(default_factory=list)  # per-seed detail, ordered by seed

    @property
    def any_pass(self) -> bool:
        return self.n_success > 0


def summarize_cell(task_id: str, model: str, rollouts: list[RolloutResult]) -> CellMetrics:
    rewards = [r.reward if r.reward is not None else 0.0 for r in rollouts]
    n = len(rollouts)
    n_success = sum(1 for r in rollouts if r.outcome is Outcome.SUCCESS)
    counts = Counter(r.outcome.value for r in rollouts)
    attempts = [
        {
            "seed": r.seed,
            "reward": r.reward,
            "outcome": r.outcome.value,
            "steps": r.steps,
            "duration_s": r.duration_s,
        }
        for r in sorted(rollouts, key=lambda r: r.seed)
    ]
    return CellMetrics(
        task_id=task_id,
        model=model,
        n_rollouts=n,
        n_success=n_success,
        n_fail=n - n_success,
        pass_rate=n_success / n if n else 0.0,
        mean_reward=mean(rewards) if rewards else 0.0,
        max_reward=max(rewards) if rewards else 0.0,
        std_reward=pstdev(rewards) if len(rewards) > 1 else 0.0,
        mean_steps=mean([r.steps for r in rollouts]) if rollouts else 0.0,
        mean_duration_s=mean([r.duration_s for r in rollouts]) if rollouts else 0.0,
        outcome_counts={o.value: counts.get(o.value, 0) for o in Outcome},
        attempts=attempts,
    )


@dataclass
class ModelMetrics:
    """Per-model rollup across all tasks — the leaderboard row."""

    model: str
    n_rollouts: int
    n_success: int
    n_fail: int
    pass_rate: float
    mean_reward: float
    mean_steps: float
    outcome_counts: dict           # Outcome.value -> count (the failure breakdown)
    by_domain: dict = field(default_factory=dict)  # app_type -> pass_rate

    @property
    def fail_breakdown(self) -> dict:
        """How the failures split — answers 'how many times / how did it fail'."""
        return {k: v for k, v in self.outcome_counts.items() if k != Outcome.SUCCESS.value}


def summarize_model(model: str, rollouts: list[RolloutResult]) -> ModelMetrics:
    n = len(rollouts)
    n_success = sum(1 for r in rollouts if r.outcome is Outcome.SUCCESS)
    counts = Counter(r.outcome.value for r in rollouts)
    rewards = [r.reward if r.reward is not None else 0.0 for r in rollouts]

    by_domain: dict[str, float] = {}
    domains = {r.app_type for r in rollouts}
    for dom in sorted(domains):
        dr = [r for r in rollouts if r.app_type == dom]
        ds = sum(1 for r in dr if r.outcome is Outcome.SUCCESS)
        by_domain[dom] = ds / len(dr) if dr else 0.0

    return ModelMetrics(
        model=model,
        n_rollouts=n,
        n_success=n_success,
        n_fail=n - n_success,
        pass_rate=n_success / n if n else 0.0,
        mean_reward=mean(rewards) if rewards else 0.0,
        mean_steps=mean([r.steps for r in rollouts]) if rollouts else 0.0,
        outcome_counts={o.value: counts.get(o.value, 0) for o in Outcome},
        by_domain=by_domain,
    )


def classify_task(
    oracle_ok: bool,
    cells: list[CellMetrics],
    *,
    easy_threshold: float = 0.99,
    breaking_max_reward: float = 0.05,
) -> Bucket:
    """Bucket a task from its oracle result + per-model cells.

    breaking_max_reward: if the best mean_reward across models is <= this AND no
    model ever passed, the task is model-breaking (no meaningful progress).
    easy_threshold: if the worst model's pass_rate >= this, it's too easy.
    """
    if not oracle_ok:
        return Bucket.BROKEN
    if not cells:
        return Bucket.MODEL_BREAKING
    any_pass = any(c.any_pass for c in cells)
    best_mean_reward = max(c.mean_reward for c in cells)
    if not any_pass and best_mean_reward <= breaking_max_reward:
        return Bucket.MODEL_BREAKING
    min_pass_rate = min(c.pass_rate for c in cells)
    if min_pass_rate >= easy_threshold:
        return Bucket.TOO_EASY
    return Bucket.PRODUCTIVE
