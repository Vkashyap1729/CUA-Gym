"""Phase 0-1 validation: run the oracle control on local web tasks (NO VM, NO model).

Proves the scaffold end-to-end: task loading -> mock hosting -> dual-env reward
anchors -> reward parsing. For every complete mock_websites task under
output/final/, starts the mock it needs, runs the oracle (initial->0.0,
golden->1.0), and reports PASS/FAIL.

Usage:
  scripts/benchmark/validate_local.py [--final-dir output/final] [--keep-servers]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# Allow `python scripts/benchmark/validate_local.py` (script run, not module).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.benchmark.oracle import DEFAULT_PORTS, detect_mock_app, oracle_check  # noqa: E402
from scripts.benchmark.tasks import load_tasks  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
START_MOCK = REPO / "scripts" / "local" / "start_mock.sh"
VENV_PY = REPO / ".venv-local" / "bin" / "python"


def load_dotenv(path: Path) -> None:
    """Minimal .env loader: export KEY=VALUE lines into os.environ (no override of
    already-set vars). LLM-judge reward.py reads OPENAI_API_KEY from the process
    env, so judge-backed tasks under-score (0.0 body) without this — mirrors the
    behavior of scripts/local/run_local_pipeline.py which loads .env itself.
    """
    import os

    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip().strip("'").strip('"')
        if key and val and not os.environ.get(key):
            os.environ[key] = val


def _wait_up(port: int, timeout: float = 60.0) -> bool:
    url = f"http://localhost:{port}/go?sid=probe"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(1.0)
    return False


def start_mock(app: str, port: int) -> subprocess.Popen:
    proc = subprocess.Popen(
        ["bash", str(START_MOCK), app, str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--final-dir", default=str(REPO / "output" / "final"))
    ap.add_argument("--keep-servers", action="store_true", help="don't kill mocks on exit")
    args = ap.parse_args()

    load_dotenv(REPO / ".env")

    tasks = load_tasks(args.final_dir)
    web = [t for t in tasks if t.is_web]
    print(f"Loaded {len(tasks)} task(s); {len(web)} web (mock_websites).")
    if not web:
        print("No web tasks to validate locally. (Desktop tasks need the VM.)")
        return 0

    # Map each task -> (mock app, port); collect the distinct mocks to launch.
    plan = []
    needed: dict[str, int] = {}
    for t in web:
        app = detect_mock_app(t)
        if app is None:
            print(f"  SKIP {t.task_id}: could not resolve a single mock app")
            continue
        port = DEFAULT_PORTS.get(app)
        if port is None:
            print(f"  SKIP {t.task_id}: no default port for mock {app!r}")
            continue
        plan.append((t, app, port))
        needed[app] = port

    servers: list[subprocess.Popen] = []
    try:
        for app, port in needed.items():
            print(f"Starting mock {app} on :{port} ...", flush=True)
            servers.append(start_mock(app, port))
        for app, port in needed.items():
            if not _wait_up(port):
                print(f"  ERROR: mock {app} did not come up on :{port}")
                return 2
            print(f"  {app} ready on :{port}")

        print("\n=== ORACLE CONTROL ===")
        results = []
        for t, app, port in plan:
            res = oracle_check(t, mock_url=f"http://localhost:{port}", python=str(VENV_PY))
            results.append(res)
            mark = "PASS" if res["ok"] else "FAIL"
            warn = f"  warnings={res['forbidden_warnings']}" if res["forbidden_warnings"] else ""
            print(
                f"  [{mark}] {t.task_id:<24} ({app}) "
                f"initial={res['reward_initial']} golden={res['reward_golden']}{warn}"
            )

        n_pass = sum(1 for r in results if r["ok"])
        print(f"\n{n_pass}/{len(results)} tasks passed the oracle control.")

        out = REPO / "output" / "benchmark" / "oracle_validation.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            __import__("json").dumps(
                {"n_tasks": len(results), "n_pass": n_pass, "results": results},
                indent=2,
            )
        )
        print(f"Wrote {out}")
        return 0 if n_pass == len(results) else 1
    finally:
        if not args.keep_servers:
            for p in servers:
                p.terminate()
            for p in servers:
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()


if __name__ == "__main__":
    raise SystemExit(main())
