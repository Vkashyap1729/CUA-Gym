# Model-benchmarking harness (`scripts/benchmark/`)

Benchmarks computer-use models (Claude + OpenAI) against verified CUA-Gym tasks
(`output/final/<id>/`) and classifies each task by **panel difficulty** — the
"model-breaking" check. This is the inverse of the generation pipeline: instead of
*producing* triples, it *runs models against them* to calibrate difficulty.

## Why an oracle control

Generation already verifies each task is solvable in principle (golden→1.0,
initial→0.0). Before attributing a 0% model pass-rate to "hard task," we re-run
that **oracle control**. Buckets:

| Bucket | Signal |
|---|---|
| **Broken** | oracle fails (`golden_patch`→reward ≠ 1.0) — task/reward bug, not the model |
| **Model-breaking** | oracle = 1.0 but ~0 pass + ~0 partial reward across all models/seeds |
| **Too-easy** | every model solves it reliably (low RLVR signal) |
| **Productive** | mixed pass/fail across models & seeds (high learning signal) |

## Panel & budget (current config)

- Models: Claude Opus + Sonnet + Haiku (computer-use), OpenAI `computer-use-preview`
- Source: `output/final/` (stratified by `app_type`), target 100 tasks
- Rollout: full GUI on the OSWorld VM; **K=5 seeds × ≤25 steps**
- Scale ≈ 100 × 4 × 5 = 2,000 rollouts — async, concurrency-capped, resumable;
  use `--pilot 10` before the full run

## Build phases

| Phase | Files | Status |
|---|---|---|
| 0 — pure layers | `tasks.py`, `actions.py`, `rewards.py`, `test_units.py` | ✅ done, unit-tested |
| 1 — oracle + loop | `oracle.py`, `agents/base.py`, `validate_local.py` | ✅ done, validated locally |
| 2 — model adapters | `agents/anthropic_cua.py`, `agents/openai_cua.py`, `agents/registry.py` | ✅ done, parsing unit-tested |
| 3 — driver | `rollout.py`, `env_backend.py`, `runner.py`, `sample_tasks.py` | ✅ done, fake-validated |
| 4 — analysis | `metrics.py`, `analysis.py` → `report.{json,md,html}` | ✅ done, fake-validated |

Everything is built and proven on the plumbing via `test_pipeline.py` (FakeBackend +
ScriptedAgent, no VM/model). Only a **live** 100×4×5 GUI run is gated on installing
`~/OSWorld-RL` + computer-use API access.

## Metrics you get out (`metrics.py`)

Per-rollout **Outcome** (exactly one): `success` (reward==1.0) · `partial` (0<r<1) ·
`zero` (r==0) · `truncated` (hit max_steps, no Done) · `error` (crash / no parseable
REWARD) · `timeout` (wall-clock). **Failure = any non-success**; `n_fail` is broken
down by these so you see *how* a model failed, not just that it did.

- Per **(task, model)** cell: `n_rollouts, n_success, n_fail, pass_rate, mean/max/std_reward, mean_steps, outcome_counts`
- Per **model** (leaderboard): `pass_rate, mean_reward, n_fail, fail_breakdown {zero,partial,truncated,error,timeout}, mean_steps, by_domain`
- Per **task** bucket: `broken` (oracle≠1.0) · `model_breaking` (oracle ok, no model progress) · `too_easy` · `productive`

## Run it end to end (once the VM is available)

```bash
python scripts/benchmark/sample_tasks.py --n 100            # -> benchmark_set.json
python -m scripts.benchmark.run_full --run-id RUN --pilot 10  # oracle + rollouts (resumable)
python scripts/benchmark/analysis.py output/benchmark/RUN   # -> report.{json,md,html}
```

## What runs today (no VM, no model)

```bash
python scripts/benchmark/test_units.py        # action codegen + reward parsing
python scripts/benchmark/validate_local.py    # oracle control on local web tasks
```

`validate_local.py` hosts each needed mock (`scripts/local/start_mock.sh`), runs the
dual-env oracle via `scripts/local/local_verify.py`, and reports PASS/FAIL. It loads
`.env` itself so LLM-judge reward components get `OPENAI_API_KEY` (otherwise
judge-backed tasks under-score to ~0.6 — an environment artifact, not a broken task).

## Action layer

`actions.py` defines a vendor-neutral action schema (`Click`, `TypeText`,
`KeyPress`, `Scroll`, `Drag`, `Wait`, `Done`, …). `to_pyautogui(action, model_size,
vm_size)` renders each into a snippet executed on the VM via `env.run_python` under
`DISPLAY=:0`, scaling coordinates from the model's screenshot space to the VM screen.
Both model adapters (Phase 2) normalize their tool calls into this schema.

## Output layout (Phase 3+)

```
output/benchmark/<run_id>/
  status.json                              # resumable, atomic writes
  benchmark_set.json                       # sampled tasks
  oracle/<task>.json                       # oracle control per task
  rollouts/<task>__<model>__<seed>.json    # full trace + final reward
  report.{md,html}                         # leaderboard + buckets
```
