"""Stratified sampling of benchmark tasks from output/final/.

Samples up to N tasks, proportionally across app_type so the panel is exercised on
a representative spread of domains. Deterministic given --seed. Writes
benchmark_set.json (a list of task_ids) consumed by runner.py.

Warn-and-use-all: if fewer than N complete tasks exist, uses all of them and says so.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.benchmark.tasks import load_tasks  # noqa: E402


def stratified_sample(tasks, n: int, seed: int = 0):
    import random

    rng = random.Random(seed)
    by_domain: dict[str, list] = defaultdict(list)
    for t in tasks:
        by_domain[t.app_type].append(t)
    for d in by_domain:
        rng.shuffle(by_domain[d])

    total = len(tasks)
    if total <= n:
        return list(tasks), total < n

    # Proportional allocation per domain, largest-remainder rounding.
    alloc: dict[str, int] = {}
    rema: dict[str, float] = {}
    for d, items in by_domain.items():
        exact = n * len(items) / total
        alloc[d] = min(len(items), int(exact))
        rema[d] = exact - int(exact)
    while sum(alloc.values()) < n:
        d = max(rema, key=lambda k: (rema[k], len(by_domain[k]) - alloc[k]))
        if alloc[d] < len(by_domain[d]):
            alloc[d] += 1
            rema[d] = -1  # don't pick again immediately
        else:
            rema[d] = -1
        if all(alloc[k] >= len(by_domain[k]) for k in alloc):
            break

    picked = []
    for d, k in alloc.items():
        picked.extend(by_domain[d][:k])
    return picked, False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--final-dir", default="output/final")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="output/benchmark/benchmark_set.json")
    args = ap.parse_args()

    tasks = load_tasks(args.final_dir)
    if not tasks:
        print(f"No complete tasks under {args.final_dir}.")
        return 1

    picked, short = stratified_sample(tasks, args.n, args.seed)
    if short:
        print(f"WARNING: only {len(picked)} complete tasks exist (< {args.n}); using all.")

    from collections import Counter

    dist = Counter(t.app_type for t in picked)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "n_requested": args.n,
        "n_selected": len(picked),
        "seed": args.seed,
        "by_domain": dict(dist),
        "task_ids": [t.task_id for t in picked],
    }, indent=2))
    print(f"Selected {len(picked)} tasks across {len(dist)} domains -> {out}")
    for d, c in sorted(dist.items()):
        print(f"  {d:<20} {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
