"""
Local dual-env verifier for mock-website tasks (NO VM).

Reproduces the adversarial loop's PASS check without Aliyun. A web-mock task's
three scripts are plain `requests` calls against a BASE_URL, so we just run them
locally against a locally-hosted mock and check the two reward anchors:

  INITIAL env:  initial_setup.py  -> reward.py   expect REWARD == 0.0
  GOLDEN  env:  initial_setup.py  -> golden_patch.py -> reward.py   expect REWARD == 1.0

Isolation between the two envs is by sid: each run of initial_setup.py mints a
fresh uuid into /tmp/task_web_sid, so the same mock server hosts both worlds.
We run the envs sequentially, clearing the sid file between them.

Localization applied to the generated scripts at run time (originals untouched):
  - https://cua-gym-<x>.xlang.ai  ->  the local mock URL
  - `google-chrome ...`           ->  `true ...`   (GUI launch is a no-op locally)

reward.py does `from reward_judge import call_llm_judge`; we put scripts/local on
PYTHONPATH so it resolves to the env-configurable judge shim (default gpt-4o).

Usage:
  python scripts/local/local_verify.py <task_dir> [--mock-url http://localhost:5173]
where <task_dir> holds initial_setup.py, golden_patch.py, reward.py.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DEFAULT_PY = str(REPO / ".venv-local" / "bin" / "python")
SID_FILE = "/tmp/task_web_sid"

# Match both hyphen and underscore host variants (e.g. cua-gym-google-calendar AND
# cua-gym-google_calendar) so multi-word mocks always get localized.
_XLANG_RE = re.compile(r"https://cua-gym-[a-z0-9_-]+\.xlang\.ai")
_REWARD_RE = re.compile(r"REWARD:\s*([0-9]*\.?[0-9]+)")

# Soft checks on reward.py (mirror the pipeline's forbidden patterns). These warn;
# the hard gate is the 0.0/1.0 anchors.
_FORBIDDEN = [
    (re.compile(r"\bimport\s+subprocess\b"), "uses subprocess"),
    (re.compile(r"\bfrom\s+openai\s+import\b"), "imports openai directly (must use reward_judge)"),
    (re.compile(r"return\s+1\.0\b"), "hardcoded `return 1.0`"),
    (re.compile(r"REWARD:\s*1\.0[\"']"), "hardcoded `REWARD: 1.0` print"),
]


def _localize(src: str, mock_url: str) -> str:
    src = _XLANG_RE.sub(mock_url, src)
    src = src.replace("google-chrome", "true")
    return src


def _write_localized(task_dir: Path, run_dir: Path, mock_url: str) -> None:
    for name in ("initial_setup.py", "golden_patch.py", "reward.py"):
        s = (task_dir / name).read_text()
        (run_dir / name).write_text(_localize(s, mock_url))


def _run(py: str, script: Path, env: dict, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        [py, str(script)],
        capture_output=True, text=True, env=env, cwd=str(script.parent), timeout=timeout,
    )


def _reward_of(stdout: str):
    m = _REWARD_RE.findall(stdout)
    return float(m[-1]) if m else None


def verify_task(task_dir, mock_url="http://localhost:5173", python=DEFAULT_PY, verbose=True):
    task_dir = Path(task_dir)
    for name in ("initial_setup.py", "golden_patch.py", "reward.py"):
        if not (task_dir / name).exists():
            return {"pass": False, "error": f"missing {name}"}

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{HERE}{os.pathsep}{REPO / 'utils'}{os.pathsep}" + env.get("PYTHONPATH", "")

    reward_src = (task_dir / "reward.py").read_text()
    warnings = [msg for rgx, msg in _FORBIDDEN if rgx.search(reward_src)]

    steps = []

    def log(msg):
        steps.append(msg)
        if verbose:
            print(msg)

    with tempfile.TemporaryDirectory(prefix="cuagym_local_") as tmp:
        run_dir = Path(tmp)
        _write_localized(task_dir, run_dir, mock_url)

        results = {}
        for env_name, scripts, expected in (
            ("initial", ["initial_setup.py", "reward.py"], 0.0),
            ("golden", ["initial_setup.py", "golden_patch.py", "reward.py"], 1.0),
        ):
            if os.path.exists(SID_FILE):
                os.remove(SID_FILE)
            reward_val = None
            ok = True
            for s in scripts:
                cp = _run(python, run_dir / s, env)
                if cp.returncode != 0:
                    log(f"[{env_name}] {s} FAILED rc={cp.returncode}: {cp.stderr.strip()[:300]}")
                    ok = False
                    break
                if s == "reward.py":
                    reward_val = _reward_of(cp.stdout)
                    log(f"[{env_name}] reward.py -> REWARD={reward_val} (expected {expected})")
                    if reward_val is None:
                        log(f"[{env_name}] no 'REWARD: X.X' in output: {cp.stdout.strip()[:300]}")
                        ok = False
            results[env_name] = {"reward": reward_val, "ran": ok, "expected": expected}

        r0 = results["initial"]["reward"]
        r1 = results["golden"]["reward"]
        passed = (r0 == 0.0) and (r1 == 1.0) and not warnings
        return {
            "pass": passed,
            "reward_initial": r0,
            "reward_golden": r1,
            "forbidden_warnings": warnings,
            "steps": steps,
        }


def main():
    ap = argparse.ArgumentParser(description="Local dual-env verifier for a web-mock task")
    ap.add_argument("task_dir")
    ap.add_argument("--mock-url", default="http://localhost:5173")
    ap.add_argument("--python", default=DEFAULT_PY)
    args = ap.parse_args()
    res = verify_task(args.task_dir, args.mock_url, args.python)
    print("\n=== VERDICT ===")
    print(f"PASS: {res['pass']}")
    print(f"reward(initial)={res.get('reward_initial')}  reward(golden)={res.get('reward_golden')}")
    if res.get("forbidden_warnings"):
        print("forbidden warnings:", res["forbidden_warnings"])
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
