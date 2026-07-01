"""CUA-Gym model-benchmarking harness.

Benchmarks computer-use models (Claude / OpenAI) against verified CUA-Gym tasks
and classifies each task by panel difficulty:

  Broken         oracle control fails (golden_patch -> reward != 1.0): task/reward bug
  Model-breaking oracle == 1.0 but no model makes progress: too hard / reward too strict
  Too-easy       every model solves it reliably: low RLVR signal
  Productive     mixed pass/fail across models & seeds: high learning signal

Layered build (see scripts/benchmark/README.md):
  Phase 0  tasks.py, actions.py, rewards.py        pure, unit-tested
  Phase 1  oracle.py + agents/base.py              single rollout, validated locally
  Phase 2  agents/anthropic_cua.py, openai_cua.py  model adapters
  Phase 3  rollout.py, runner.py, sample_tasks.py  async resumable driver
  Phase 4  analysis.py                             buckets + leaderboard + report
"""

__all__ = ["tasks", "actions", "rewards"]
