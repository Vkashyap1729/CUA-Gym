"""Run a REAL benchmark on mock_websites tasks LOCALLY (Playwright, no Aliyun VM).

One command: starts the mocks each task needs, runs the real oracle control per
task, drives the model panel through a headless browser, and renders the report.

  # validate access + plumbing cheaply first
  python scripts/benchmark/run_web.py --run-id pilot --pilot 3 --models claude-opus openai-cua --seeds 2
  # full web run
  python scripts/benchmark/run_web.py --run-id web_full --seeds 5

Notes:
  * Uses the shared /tmp/task_web_sid file, so concurrency is forced to 1.
  * Loads .env so model keys + the reward LLM-judge key are present.
  * Makes live, paid model API calls — scope with --pilot / --models / --seeds.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.benchmark.agents.registry import build_agent, panel_keys  # noqa: E402
from scripts.benchmark.analysis import write_reports  # noqa: E402
from scripts.benchmark.oracle import DEFAULT_PORTS, detect_mock_app, oracle_check_web  # noqa: E402
from scripts.benchmark.runner import run_benchmark  # noqa: E402
from scripts.benchmark.tasks import load_task, load_tasks  # noqa: E402
from scripts.benchmark.web_backend import PlaywrightWebBackend  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
VENV_PY = REPO / ".venv-local" / "bin" / "python"


# API keys in .env MUST win over any stale value exported in the shell/profile
# (a stale ANTHROPIC_API_KEY otherwise causes 401s — see scripts/local notes).
_FORCE_OVERRIDE = {"ANTHROPIC_API_KEY", "OPENAI_API_KEY"}


def load_dotenv(path: Path) -> None:
    import os

    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip("'").strip('"')
            if k and v and (k in _FORCE_OVERRIDE or not os.environ.get(k)):
                os.environ[k] = v


def wait_up(port: int, timeout: float = 60) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/go?sid=probe", timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--final-dir", default="output/final")
    ap.add_argument("--models", nargs="*", default=panel_keys())
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--max-steps", type=int, default=25)
    ap.add_argument("--pilot", type=int, default=0, help="cap to first N tasks")
    ap.add_argument("--task-ids", nargs="*", default=None, help="explicit task ids to run")
    ap.add_argument("--out-root", default=str(REPO / "output" / "benchmark"),
                    help="where run dirs are written (move off output/ if it's volatile)")
    ap.add_argument("--headless", action="store_true", default=True)
    args = ap.parse_args()

    load_dotenv(REPO / ".env")

    # Resolve tasks -> mock app -> port; only web tasks are supported here.
    all_tasks = load_tasks(args.final_dir)
    web = [t for t in all_tasks if t.is_web]
    if args.task_ids:
        wanted = set(args.task_ids)
        web = [t for t in web if t.task_id in wanted]
    if args.pilot:
        web = web[: args.pilot]
    if not web:
        print("No web tasks found.")
        return 1

    task_app: dict[str, str] = {}
    needed: dict[str, int] = {}
    for t in web:
        app = detect_mock_app(t)
        port = DEFAULT_PORTS.get(app) if app else None
        if not port:
            print(f"  SKIP {t.task_id}: unresolved mock ({app})")
            continue
        task_app[t.task_id] = app
        needed[app] = port
    task_ids = [t.task_id for t in web if t.task_id in task_app]

    n = len(task_ids) * len(args.models) * args.seeds
    print(f"REAL web run: {len(task_ids)} tasks x {len(args.models)} models x {args.seeds} seeds = {n} rollouts")
    print(f"  models: {args.models}  ·  mocks: {needed}")

    servers = []
    try:
        for app, port in needed.items():
            servers.append(subprocess.Popen(
                ["bash", str(REPO / "scripts/local/start_mock.sh"), app, str(port)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        for app, port in needed.items():
            if not wait_up(port):
                print(f"  ERROR: mock {app} did not start on :{port}")
                return 2
            print(f"  {app} ready on :{port}")

        def backend_factory(task):
            app = task_app[task.task_id]
            return PlaywrightWebBackend(
                mock_url=f"http://localhost:{DEFAULT_PORTS[app]}",
                python=str(VENV_PY), headless=args.headless)

        def oracle_fn(task):
            app = task_app[task.task_id]
            return oracle_check_web(task, f"http://localhost:{DEFAULT_PORTS[app]}", str(VENV_PY))

        run_dir = Path(args.out_root) / args.run_id
        summary = run_benchmark(
            run_dir=run_dir, task_ids=task_ids, final_dir=args.final_dir,
            models=args.models, seeds=args.seeds, max_steps=args.max_steps,
            concurrency=1,  # shared sid file
            backend_factory=backend_factory, agent_factory=build_agent, oracle_fn=oracle_fn,
        )
        print("summary:", summary)
        write_reports(run_dir)
        print(f"\nReport: open {run_dir}/index.html   (also report.html, report_detail.html)")
        return 0
    finally:
        for p in servers:
            p.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
