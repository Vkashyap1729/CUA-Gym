"""
Config-driven local generator (NO VM) — pick types + counts, get verified tasks.

One command runs the whole local pipeline for one or more mock apps. Per app it:
  1. auto-hosts the mock locally (npm run dev on the configured port)
  2. STAGE 1 — generates `count` task SPECS via `claude -p` (schema-grounded)
              -> output/task_generation/<app>.json
  3. STAGE 2 — runs the adversarial loop over those specs (reuses run_local_pipeline)
              -> output/final/<id>/
  4. stops the mock

Configure in scripts/local/config.json (apps = [{name, count, port}], max_rounds,
judge_model), or override on the CLI.

Examples:
  python scripts/local/generate.py                          # use config.json as-is
  python scripts/local/generate.py --app gmail --count 100  # one app, 100 tasks
  python scripts/local/generate.py --app google_calendar --count 30 --regen
  python scripts/local/generate.py --only gmail --max-rounds 3
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
import run_local_pipeline as loop  # noqa: E402  (process_task, load_specs, run_agent, load_dotenv, status helpers)

CONFIG = HERE / "config.json"
TASKGEN = REPO / "output" / "task_generation"

SPEC_PROMPT = """You are the task-gen agent for CUA-Gym, generating task SPECIFICATIONS for the \
"{app}" mock web app (domain: mock_websites).

FIRST read the state schema so every task is grounded in real fields:
- {schema}

Generate EXACTLY {count} diverse, evaluable tasks. Spread difficulty (~30% easy, ~45% medium,
~25% hard) and cover the app's main action types (don't repeat the same action).

Write a JSON array to this exact path using the Write tool: {out}
Each element MUST be:
{{
  "task_id": "{app}_001",            // sequential, zero-padded to 3 digits
  "domain": "mock_websites",
  "app": "{app}",
  "task_instruction": "<natural, goal-oriented; describe the GOAL not the method; vary phrasing>",
  "context": "<ground truth: the INITIAL state to build (specific entities/names/dates, incl. distractors that must stay untouched) AND the EXPECTED end state after the task; concrete enough to build and verify unambiguously>",
  "difficulty": "easy|medium|hard"
}}

Rules: unique verifiable end-state per task; realistic content; include distractors so over-action
can be penalized. Write ONLY that one JSON file. When done, print DONE.
"""


def schema_path(app: str) -> Path:
    return REPO / ".claude" / "skills" / "mock_websites" / "schemas" / f"{app}_mock.md"


def mock_dir(app: str) -> Path:
    return REPO / "hub" / "websites" / f"{app}_mock"


def _port_alive(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/go?sid=probe", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def start_mock(app: str, port: int):
    """Start the mock if not already serving on `port`. Returns the Popen (or None if reused)."""
    if _port_alive(port):
        print(f"  mock {app} already live on :{port} — reusing")
        return None
    d = mock_dir(app)
    if not (d / "node_modules").exists():
        print(f"  installing deps for {app}_mock (first run)...")
        subprocess.run(["npm", "install", "--silent"], cwd=str(d), check=True)
    print(f"  starting {app}_mock on :{port} ...")
    proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", str(port), "--host"],
        cwd=str(d), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(40):
        if _port_alive(port):
            print(f"  mock {app} ready on :{port}")
            return proc
        time.sleep(0.5)
    raise RuntimeError(f"mock {app} did not become ready on :{port}")


def stop_mock(proc):
    if proc is None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        proc.terminate()


BATCH_SIZE = 12  # ask for a few at a time; one-shot large counts under-deliver


def _load_raw(path: Path) -> list:
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict) and "tasks" in data:
        data = data["tasks"]
    return data if isinstance(data, list) else [data]


def gen_specs(app: str, count: int, regen: bool) -> Path:
    """Generate `count` specs reliably by batching + topping up until the target is met."""
    TASKGEN.mkdir(parents=True, exist_ok=True)
    out = TASKGEN / f"{app}.json"
    collected: list = []
    if out.exists() and not regen:
        collected = _load_raw(out)
        if len(collected) >= count:
            print(f"  specs exist ({len(collected)}) — reusing (use --regen to rebuild)")
            return out  # already enough

    attempts, max_attempts = 0, (count // BATCH_SIZE) + 6
    while len(collected) < count and attempts < max_attempts:
        attempts += 1
        n = min(BATCH_SIZE, count - len(collected))
        bpath = TASKGEN / f"{app}.batch.json"
        if bpath.exists():
            bpath.unlink()
        prompt = SPEC_PROMPT.format(app=app, schema=schema_path(app), count=n, out=bpath)
        print(f"  [specs] {app}: batch of {n} (have {len(collected)}/{count}), attempt {attempts}")
        loop.run_agent("task-gen", prompt, cwd=REPO, timeout=900)
        if not bpath.exists():
            print("    batch produced no file; retrying")
            continue
        try:
            batch = _load_raw(bpath)
        except Exception as e:  # noqa: BLE001
            print(f"    batch JSON invalid ({e}); retrying")
            continue
        collected.extend(batch)
        bpath.unlink(missing_ok=True)

    collected = collected[:count]
    for i, s in enumerate(collected, 1):  # renumber sequentially + enforce routing fields
        s["task_id"] = f"{app}_{i:03d}"
        s["domain"] = "mock_websites"
        s["app"] = app
    out.write_text(json.dumps(collected, indent=2))
    if len(collected) < count:
        print(f"  WARNING: only {len(collected)}/{count} specs produced for {app}")
    else:
        print(f"  generated {len(collected)} specs -> {out}")
    return out


def run_app(app: str, count: int, port: int, max_rounds: int, regen: bool, only_ids):
    print(f"\n=== {app}: target {count} tasks on :{port} ===")
    if not mock_dir(app).exists():
        print(f"  SKIP: {mock_dir(app)} missing (git submodule update --init?)")
        return
    if not schema_path(app).exists():
        print(f"  SKIP: schema {schema_path(app)} missing")
        return

    proc = start_mock(app, port)
    mock_url = f"http://localhost:{port}"
    status = loop.load_status()
    try:
        specs = loop.load_specs(str(gen_specs(app, count, regen)))[:count]
        if only_ids:
            specs = [s for s in specs if s["id"] in only_ids]
        for i, spec in enumerate(specs, 1):
            spec["app"] = app
            if status.get(spec["id"], {}).get("status") == "completed":
                print(f"  [{i}/{len(specs)}] {spec['id']}: already done")
                continue
            print(f"  [{i}/{len(specs)}] {spec['id']}: adversarial loop...")
            try:
                res = loop.process_task(spec, mock_url, max_rounds)
            except Exception as e:  # noqa: BLE001
                res = {"status": "error", "error": str(e)}
            status[spec["id"]] = res
            loop.save_status(status)
            mark = {"completed": "OK", "failed": "FAIL"}.get(res["status"], res["status"])
            print(f"      -> {mark} (init={res.get('reward_initial')} gold={res.get('reward_golden')})")
    finally:
        stop_mock(proc)
    done = sum(1 for s in status.values() if s.get("status") == "completed")
    print(f"  {app}: {done} total verified in output/final/")


def main():
    ap = argparse.ArgumentParser(description="Config-driven local task generator (no VM)")
    ap.add_argument("--config", default=str(CONFIG))
    ap.add_argument("--app", help="run only this app (overrides config app list)")
    ap.add_argument("--count", type=int, help="override task count for the app")
    ap.add_argument("--port", type=int, help="override port for --app")
    ap.add_argument("--max-rounds", type=int)
    ap.add_argument("--regen", action="store_true", help="regenerate specs even if they exist")
    ap.add_argument("--only", help="comma-separated task_ids to run")
    args = ap.parse_args()

    loop.load_dotenv()
    cfg = json.loads(Path(args.config).read_text())
    max_rounds = args.max_rounds or cfg.get("max_rounds", 5)
    os.environ.setdefault("CUA_GYM_JUDGE_MODEL", cfg.get("judge_model", "gpt-4o"))
    only_ids = set(args.only.split(",")) if args.only else None

    if args.app:
        apps = [{"name": args.app,
                 "count": args.count or 50,
                 "port": args.port or 5173}]
    else:
        apps = cfg["apps"]
        if args.count:
            for a in apps:
                a["count"] = args.count

    print(f"Local generator | judge={os.environ['CUA_GYM_JUDGE_MODEL']} | max_rounds={max_rounds}")
    for a in apps:
        run_app(a["name"], a["count"], a["port"], max_rounds, args.regen, only_ids)
    print("\nAll done. Verified tasks -> output/final/")


if __name__ == "__main__":
    main()
