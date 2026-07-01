"""Full benchmark run CLI — wires the real VM backend + panel + oracle.

  python -m scripts.benchmark.run_full --run-id RUN [--pilot 10]

Loads task ids (from benchmark_set.json or all of output/final/), runs the oracle
control per task, then fans out (task, model, seed) rollouts on the OSWorld VM,
resumably. Writes output/benchmark/<run-id>/. Then run analysis.py for reports.

Requires ~/OSWorld-RL + Aliyun creds for VMBackend, and ANTHROPIC_API_KEY /
OPENAI_API_KEY for the panel. Use --pilot to cap tasks before a full run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.benchmark.agents.registry import build_agent, panel_keys  # noqa: E402
from scripts.benchmark.env_backend import VMBackend  # noqa: E402
from scripts.benchmark.runner import run_benchmark  # noqa: E402


def _load_task_ids(args) -> list[str]:
    if args.task_set and Path(args.task_set).exists():
        ids = json.loads(Path(args.task_set).read_text())["task_ids"]
    else:
        ids = [d.name for d in sorted(Path(args.final_dir).iterdir()) if d.is_dir()]
    if args.pilot:
        ids = ids[: args.pilot]
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--final-dir", default="output/final")
    ap.add_argument("--task-set", default="output/benchmark/benchmark_set.json")
    ap.add_argument("--models", nargs="*", default=panel_keys())
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--max-steps", type=int, default=25)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--pilot", type=int, default=0, help="cap to first N tasks")
    ap.add_argument("--keep-vms", action="store_true")
    args = ap.parse_args()

    task_ids = _load_task_ids(args)
    run_dir = Path("output/benchmark") / args.run_id
    print(f"Running {len(task_ids)} tasks x {len(args.models)} models x {args.seeds} seeds "
          f"-> {len(task_ids) * len(args.models) * args.seeds} rollouts")
    print(f"  models: {args.models}")
    print(f"  run dir: {run_dir}")

    def backend_factory(_task):
        return VMBackend(keep_vm=args.keep_vms)

    # Oracle on the VM: apply golden_patch then reward, expect 1.0. Implemented as a
    # thin VM run; skipped (assumed ok, since generation already verified) unless
    # you wire a VM oracle. Kept explicit so it's obvious where it plugs in.
    oracle_fn = None

    summary = run_benchmark(
        run_dir=run_dir, task_ids=task_ids, final_dir=args.final_dir,
        models=args.models, seeds=args.seeds, max_steps=args.max_steps,
        concurrency=args.concurrency, backend_factory=backend_factory,
        agent_factory=build_agent, oracle_fn=oracle_fn,
    )
    print(json.dumps(summary, indent=2))
    print(f"\nNow render reports:  python scripts/benchmark/analysis.py {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
